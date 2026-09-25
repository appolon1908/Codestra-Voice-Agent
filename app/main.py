from fastapi import FastAPI,Header,HTTPException
from pydantic import BaseModel
import os,urllib.request,urllib.error,json,uuid
app=FastAPI(title="Codestra Voice Agent API",version="0.3.0")
TOKEN=os.getenv("VOICE_API_TOKEN","")
K=os.getenv("KOKORO_URL","http://host.docker.internal:8880")
P=os.getenv("PIPER_URL","http://host.docker.internal:18101")
F=os.getenv("F5_URL","http://host.docker.internal:18102")
D=os.getenv("DJONE_URL","http://host.docker.internal:8092")
DT=os.getenv("DJONE_API_TOKEN","")
def auth(a):
 if TOKEN and a!="Bearer "+TOKEN: raise HTTPException(401,"unauthorized")
class Speech(BaseModel):
 text:str; voice:str="af_heart"; language:str="en"; store:bool=True; provider:str="kokoro"
@app.get("/health")
def health(): return {"status":"ok","service":"codestra-voice-agent","version":"0.3.0"}
@app.get("/ready")
def ready(): return {"ready":True,"tts_url":K,"djone_url":D}
@app.get("/v1/providers")
def providers(authorization:str|None=Header(None)):
 auth(authorization); return {"tts":{"kokoro":K,"piper":P,"f5":F},"library":{"djone":D},"agents":["pipecat","livekit"],"mixxx":"codestra-mixxx-native"}
@app.post("/v1/speech")
def speech(s:Speech,authorization:str|None=Header(None)):
 auth(authorization)
 if s.provider not in {"kokoro","piper","f5"}: raise HTTPException(422,"unsupported provider")
 url={"kokoro":K,"piper":P,"f5":F}[s.provider]
 payload=json.dumps({"model":s.provider,"input":s.text,"voice":s.voice,"response_format":"wav"}).encode()
 req=urllib.request.Request(url+"/v1/audio/speech",data=payload,headers={"Content-Type":"application/json"},method="POST")
 try: audio=urllib.request.urlopen(req,timeout=120).read()
 except Exception as e: raise HTTPException(502,"tts provider unavailable: "+type(e).__name__)
 os.makedirs("/audio",exist_ok=True); name=str(uuid.uuid4())+".wav"; path="/audio/"+name
 open(path,"wb").write(audio)
 stored=None
 if s.store and DT:
  body=json.dumps({"path":"/music/Generated/"+name,"source":"voice-agent","provenance":"generated:"+s.provider}).encode()
  q=urllib.request.Request(D+"/v1/library/tracks",data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+DT},method="POST")
  try: stored=json.loads(urllib.request.urlopen(q,timeout=10).read())
  except Exception as e: stored={"error":type(e).__name__}
 return {"completed":True,"provider":s.provider,"voice":s.voice,"audio_file":name,"library":stored}
