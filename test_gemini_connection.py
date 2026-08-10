#!/usr/bin/env python3
"""
Test script to verify Gemini Live connection.
Mimics agent.html behavior without needing audio/browser.
"""

import asyncio
import json
import websockets
import requests
import sys

SERVER_URL = "http://localhost:8000"

async def test_gemini_connection():
    print("1. Fetching Gemini token...")
    try:
        resp = requests.post(f"{SERVER_URL}/api/token")
        if resp.status_code != 200:
            print(f"   ERROR: Token fetch failed: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False
        
        data = resp.json()
        token = data["token"]
        model = data["model"]
        print(f"   ✓ Token received: {token[:20]}...")
        print(f"   ✓ Model: {model}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return False
    
    print("\n2. Connecting to Gemini Live WebSocket...")
    ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained?access_token={token}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("   ✓ WebSocket connected")
            
            print("\n3. Sending setup message...")
            setup_msg = {
                "setup": {
                    "model": f"models/{model}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "temperature": 1.0,
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": "Puck"}
                            }
                        }
                    },
                    "systemInstruction": {
                        "parts": [{"text": "You are a helpful AI assistant. Greet the user briefly."}]
                    },
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {}
                }
            }
            
            await ws.send(json.dumps(setup_msg))
            print("   ✓ Setup message sent")
            
            print("\n4. Waiting for setupComplete...")
            setup_complete = False
            message_count = 0
            
            while message_count < 10:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(message)
                    message_count += 1
                    
                    if "setupComplete" in data:
                        print("   ✓ setupComplete received!")
                        setup_complete = True
                        
                        print("\n5. Sending test prompt...")
                        test_prompt = {
                            "clientContent": {
                                "turns": [{"role": "user", "parts": [{"text": "Say 'Hello, I'm connected and working!'"}]}],
                                "turnComplete": True
                            }
                        }
                        await ws.send(json.dumps(test_prompt))
                        print("   ✓ Test prompt sent")
                        
                    elif data.get("serverContent"):
                        sc = data["serverContent"]
                        if sc.get("modelTurn", {}).get("parts"):
                            for part in sc["modelTurn"]["parts"]:
                                if part.get("text"):
                                    print(f"   📝 Text: {part['text'][:100]}")
                                if part.get("inlineData"):
                                    print(f"   🔊 Audio data received ({len(part['inlineData'].get('data', ''))} bytes)")
                        
                        if sc.get("outputTranscription"):
                            text = sc["outputTranscription"].get("text", "")
                            if text:
                                print(f"   💬 Transcription: {text}")
                    
                    else:
                        print(f"   ℹ️  Message {message_count}: {list(data.keys())}")
                        
                except asyncio.TimeoutError:
                    print("   ⚠️  No message received in 10s")
                    break
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"   ❌ Connection closed: {e}")
                    break
            
            if setup_complete:
                print("\n✅ SUCCESS: Gemini Live connection working!")
                return True
            else:
                print("\n❌ FAILED: setupComplete not received")
                return False
                
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Gemini Live Connection Test")
    print("=" * 60)
    print()
    
    success = asyncio.run(test_gemini_connection())
    
    print()
    print("=" * 60)
    if success:
        print("Test PASSED - Agent should work in meeting")
    else:
        print("Test FAILED - Check token format and network")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
