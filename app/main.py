from fastapi import FastAPI,Header,HTTPException
from pydantic import BaseModel
import os
app=FastAPI(title="Codestra Voice Agent API",version="0.2.0")
TOKEN=os.getenv("VOICE_API_TOKEN","")
def auth(a):
 if TOKEN and a!="Bearer "+TOKEN: raise HTTPException(401,"unauthorized")
class Speech(BaseModel):
 text:str; voice:str="af_heart"; language:str="en"; store:bool=True
@app.get("/health")
def health(): return {"status":"ok","service":"codestra-voice-agent","version":"0.2.0"}
@app.get("/ready")
def ready(): return {"ready":bool(os.getenv("KOKORO_URL")),"tts":"kokoro","djone_configured":bool(os.getenv("DJONE_URL"))}
@app.get("/v1/providers")
def providers(authorization:str|None=Header(None)):
 auth(authorization); return {"tts":{"kokoro":os.getenv("KOKORO_URL","http://kokoro:8880")},"library":{"djone":os.getenv("DJONE_URL","http://djone:8090")},"agents":["pipecat","livekit"],"mixxx":"codestra-mixxx-native"}
@app.post("/v1/speech")
def speech(s:Speech,authorization:str|None=Header(None)):
 auth(authorization); return {"accepted":True,"text":s.text,"voice":s.voice,"language":s.language,"store":s.store,"provider":"kokoro","status":"QUEUED"}
