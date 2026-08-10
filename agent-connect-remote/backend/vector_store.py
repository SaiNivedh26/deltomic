from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from backend.db import get_cursor

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"


def _get_bedrock_client():
    """Get Bedrock Runtime client with bearer token auth."""
    try:
        api_key = os.getenv("BEDROCK_API_KEY", "")
        if api_key:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = api_key
        
        region = os.getenv("BEDROCK_REGION", "us-east-1")
        return boto3.client("bedrock-runtime", region_name=region)
    except Exception as e:
        logger.warning(f"Could not initialize Bedrock client: {e}")
        return None


_bedrock_client = None


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = _get_bedrock_client()
    return _bedrock_client


def embed_text(text: str) -> list[float] | None:
    """Generate embedding using Amazon Titan Embeddings v2."""
    client = _get_client()
    if not client:
        return None
    
    try:
        body = json.dumps({
            "inputText": text,
            "dimensions": EMBEDDING_DIM,
            "normalize": True
        })
        
        response = client.invoke_model(
            modelId=EMBEDDING_MODEL,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding")
        
        if not embedding:
            logger.error("No embedding in response")
            return None
        
        return embedding
        
    except ClientError as e:
        logger.error(f"Bedrock API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None


def store_session_embedding(
    session_id: str,
    tenant_id: str | None,
    text: str,
    content_type: str = "summary",
    issue_category: str = "",
    resolution_status: str = "",
) -> str | None:
    embedding = embed_text(text)
    if not embedding:
        logger.warning(f"Skipping embedding store for session {session_id}: embedding generation failed")
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO session_embeddings
            (session_id, tenant_id, embedding, content_type, content_text, issue_category, resolution_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (session_id, tenant_id, str(embedding), content_type, text, issue_category, resolution_status),
        )
        row = cur.fetchone()
        emb_id = str(row["id"]) if row else None
        logger.info(f"Stored embedding {emb_id} for session {session_id}")
        return emb_id


def find_similar_sessions(
    query_text: str,
    tenant_id: str | None = None,
    limit: int = 5,
    min_similarity: float = 0.7,
) -> list[dict]:
    embedding = embed_text(query_text)
    if not embedding:
        return []

    with get_cursor() as cur:
        if tenant_id:
            cur.execute(
                """
                SELECT se.*, sh.task_description, sh.summary, sh.started_at
                FROM session_embeddings se
                LEFT JOIN session_history sh ON sh.id = se.session_id
                WHERE se.tenant_id = %s
                ORDER BY se.embedding <=> %s::vector
                LIMIT %s
                """,
                (tenant_id, str(embedding), limit),
            )
        else:
            cur.execute(
                """
                SELECT se.*, sh.task_description, sh.summary, sh.started_at
                FROM session_embeddings se
                LEFT JOIN session_history sh ON sh.id = se.session_id
                ORDER BY se.embedding <=> %s::vector
                LIMIT %s
                """,
                (str(embedding), limit),
            )

        results = []
        for row in cur.fetchall():
            d = dict(row)
            d["similarity_score"] = d.get("similarity_score", 0.0)
            results.append(d)
        return results


def find_similar_issues(
    query_text: str,
    issue_category: str | None = None,
    limit: int = 10,
) -> list[dict]:
    embedding = embed_text(query_text)
    if not embedding:
        return []

    with get_cursor() as cur:
        if issue_category:
            cur.execute(
                """
                SELECT se.*, sh.task_description, sh.summary, sh.started_at, sh.resolution_status
                FROM session_embeddings se
                LEFT JOIN session_history sh ON sh.id = se.session_id
                WHERE se.issue_category = %s
                ORDER BY se.embedding <=> %s::vector
                LIMIT %s
                """,
                (issue_category, str(embedding), limit),
            )
        else:
            cur.execute(
                """
                SELECT se.*, sh.task_description, sh.summary, sh.started_at, sh.resolution_status
                FROM session_embeddings se
                LEFT JOIN session_history sh ON sh.id = se.session_id
                ORDER BY se.embedding <=> %s::vector
                LIMIT %s
                """,
                (str(embedding), limit),
            )
        return [dict(r) for r in cur.fetchall()]


def get_top_issues_this_week(limit: int = 10) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT issue_category, COUNT(*) as count,
                   ARRAY_AGG(DISTINCT content_text) as sample_texts
            FROM session_embeddings
            WHERE created_at >= now() - INTERVAL '7 days'
            AND issue_category IS NOT NULL AND issue_category != ''
            GROUP BY issue_category
            ORDER BY count DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_embedding_stats() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) as total FROM session_embeddings")
        total = cur.fetchone()
        cur.execute(
            """
            SELECT COUNT(*) as weekly FROM session_embeddings
            WHERE created_at >= now() - INTERVAL '7 days'
            """
        )
        weekly = cur.fetchone()
        cur.execute(
            """
            SELECT issue_category, COUNT(*) as count
            FROM session_embeddings
            WHERE created_at >= now() - INTERVAL '7 days'
            AND issue_category IS NOT NULL
            GROUP BY issue_category
            ORDER BY count DESC
            LIMIT 5
            """
        )
        categories = [dict(r) for r in cur.fetchall()]
        return {
            "total_embeddings": total["total"] if total else 0,
            "weekly_embeddings": weekly["weekly"] if weekly else 0,
            "top_categories": categories,
        }
