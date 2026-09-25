from fastapi import FastAPI
from pydantic import BaseModel
import os
app=FastAPI(title="Codestra Voice Agent API",version="0.1.0")
class Speech(BaseModel): text:str; voice:str="af_heart"; language:str="en"
@app.get("/health")
def health(): return {"status":"ok","service":"codestra-voice-agent"}
@app.get("/v1/providers")
def providers(): return {"tts":["kokoro"],"agents":["pipecat","livekit"],"mixxx":"codestra-mixxx-native"}
@app.post("/v1/speech")
def speech(s:Speech): return {"accepted":True,"text":s.text,"voice":s.voice,"language":s.language,"provider":"kokoro","status":"QUEUED"}
