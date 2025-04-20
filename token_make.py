"""
from livekit import api #AccessToken, VideoGrant
import time, os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
api_key = 'APIExkGGUNFjwB9'#os.environ["LIVEKIT_API_KEY"]
api_secret = 'vXPYQeWS7I1GOAW1yDgRa9L3q1yJWMgNyg0qDXVcRKH'  #os.environ["LIVEKIT_API_SECRET"]

#grant = VideoGrant(room="my-demo-room")
token = api.AccessToken(api_key, api_secret)
participant_token = token.to_jwt()
print(participant_token)
"""

from livekit import api
import os

api_key = 'APIExkGGUNFjwB9'#os.environ["LIVEKIT_API_KEY"]
api_secret = 'vXPYQeWS7I1GOAW1yDgRa9L3q1yJWMgNyg0qDXVcRKH'  #os.environ["LIVEKIT_API_SECRET"]

token = api.AccessToken(api_key, api_secret) \
    .with_identity("talhakhan7367") \
    .with_name("") \
    .with_grants(api.VideoGrants(
        room_join=True,
        room="voice_assistant_room_484",
    )).to_jwt()

print(token)