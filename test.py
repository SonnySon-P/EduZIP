from database import *
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from connection_manager import manager
from schemas import *
from security import *
from typing import Any, Dict, List
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_date_base()
    yield

app = FastAPI(lifespan = lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

@app.get("/")
def read_root() -> Dict[str, str]:
    return {"message": "Welcome to the Real-Time Chat API"}

@app.post("/register")
async def register(data: RegisterSchema) -> Dict[str, str]:
    hashed = PasswordTool.hash_password(data.password)

    try:
        await create_user(data.username, hashed)

    except:
        raise HTTPException(400, "username exists")

    return {"message": "registered"}

@app.post("/login")
async def login(data: LoginSchema) -> Dict[str, str]:
    user = await find_user_by_username(data.username)

    if not user:
        raise HTTPException(401, "invalid")

    valid = PasswordTool.verify_password(data.password, user[1])

    if not valid:
        raise HTTPException(401, "invalid")

    token = JWTTool.create_token({
        "user_id": user[0]
    })

    return {
        "access_token": token
    }

@app.post("/change-password")
async def change_password(data: ChangePasswordSchema, authorization: str = Header(...)) -> Dict[str, str]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization  # 把Bearer拿掉
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")
        user = await find_user_by_id(user_id)

    except Exception:
        raise HTTPException(401, "Invalid token or expired")

    if not user:
        raise HTTPException(404, "User not found")

    is_old_password_valid = PasswordTool.verify_password(data.old_password, user[2])
    if not is_old_password_valid:
        raise HTTPException(400, "Old password is incorrect")

    new_hashed_password = PasswordTool.hash_password(data.new_password)

    try:
        await update_user_password(user[0], new_hashed_password)

    except Exception:
        raise HTTPException(500, "Database update failed")

    return {"message": "Password updated successfully"}

@app.get("/users/search")
async def search_users(keyword: str = Query(..., min_length = 1), authorization: str = Header(...)) -> Dict[str, List[Any]]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
        
    results = await search_users_by_keyword(keyword, user_id)

    return {"users": results}

@app.post("/friends/request")
async def request_friend(data: FriendRequestSchema, authorization: str = Header(...)) -> Dict[str, str]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
        
    if user_id == data.friend_id:
        raise HTTPException(400, "You cannot add yourself as a friend")

    success = await send_friend_request(user_id, data.friend_id)
    if not success:
        raise HTTPException(400, "Friend request already sent or error occurred")
        
    return {"message": "Friend request sent successfully"}

@app.get("/friends/requests/pending")
async def list_pending_requests(authorization: str = Header(...)) -> Dict[str, List[Any]]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")

    pending_list = await get_pending_friend_requests(user_id)

    return {"pending_requests": pending_list}

@app.post("/friends/accept")
async def accept_friend(data: AcceptFriendSchema, authorization: str = Header(...)) -> Dict[str, str]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")  # 被加的人

    except Exception:
        raise HTTPException(401, "Invalid token or expired")

    await accept_friend_request(user_id, data.friend_id)

    return {"message": "You are now friends!"}

@app.get("/friends")
async def list_friends(authorization: str = Header(...)) -> Dict[str, List[Any]]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")

    friends_list = await get_my_friends(user_id)

    return {"friends": friends_list}

@app.delete("/friends")
async def delete_friend(data: DeleteFriendSchema, authorization: str = Header(...)) -> Dict[str, str]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
        
    deleted = await delete_friend_relationship(user_id, data.friend_id)
    
    if not deleted:
        raise HTTPException(404, "Friend relationship or request not found")
        
    return {"message": "Friend relationship or request removed successfully"}

@app.post("/chatrooms")
async def add_chatroom(data: CreateChatroomSchema, authorization: str = Header(...)) -> Dict[str, Any]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")

    room_id = await create_chatroom(data.chatroom_name)

    if not room_id:
        raise HTTPException(500, "Failed to create chatroom")
    
    joined_success = await add_member_to_room(room_id, user_id)

    if not joined_success:
        raise HTTPException(500, "Chatroom created, but failed to join the creator to the member list")

    return {
        "message": "Chatroom created successfully",
        "room_id": room_id
    }

@app.get("/chatrooms")
async def list_chatrooms(authorization: str = Header(...)) -> Dict[str, List[Any]]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
    
    rooms = await get_user_chatrooms(user_id)

    return {"chatrooms": rooms}

@app.get("/chatrooms/me")
async def list_my_chatrooms(authorization: str = Header(...)) -> Dict[str, List[Any]]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
    
    rooms = await get_user_chatrooms(user_id)

    return {"my_chatrooms": rooms}

@app.post("/chatrooms/members")
async def add_chatroom_member(data: AddMemberSchema, authorization: str = Header(...)) -> Dict[str, str]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        current_user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
    
    is_member = await is_user_in_chatroom(data.room_id, current_user_id)
    if not is_member:
        raise HTTPException(403, "You are not a member of this chatroom")
        
    are_they_friends = await is_friend(current_user_id, data.user_id)
    if not are_they_friends:
        raise HTTPException(400, "You can only invite users who are on your friends list")
        
    invitee_in_room = await is_user_in_chatroom(data.room_id, data.user_id)
    if invitee_in_room:
        raise HTTPException(400, "This user is already a member of the chatroom")

    success = await add_member_to_room(data.room_id, data.user_id)
    
    if not success:
        raise HTTPException(500, "User is already in this chatroom or error occurred")
        
    return {"message": f"Successfully added friend (ID: {data.user_id}) to chatroom (ID: {data.room_id})"}

@app.post("/chatrooms/{room_id}/leave")
async def leave_chatroom_endpoint(room_id: int, authorization: str = Header(...)) -> Dict[str, str]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        current_user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
    
    is_member = await is_user_in_chatroom(room_id, current_user_id)
    if not is_member:
        raise HTTPException(400, "You are not a member of this chatroom")
        
    success = await remove_member_from_room(room_id, current_user_id)
    
    if not success:
        raise HTTPException(500, "Failed to leave the chatroom due to a database error")
        
    try:
        manager.disconnect(room_id, current_user_id)
        await manager.broadcast(room_id, {
            "type": "system",
            "content": f"User {current_user_id} has left the chatroom"
        })
    except Exception:
        pass

    return {"message": "You have successfully left the chatroom"}

@app.delete("/chatrooms/{room_id}")
async def delete_chatroom_endpoint(room_id: int, authorization: str = Header(...)) -> Dict[str, str]:
    try:
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = JWTTool.verify_token(token)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
    
    is_member = await is_user_in_chatroom(room_id, user_id)
    if not is_member:
        raise HTTPException(403, "You are not a member of this chatroom")
        
    success = await delete_chatroom(room_id)
    
    if not success:
        raise HTTPException(500, "Failed to delete chatroom or chatroom not found")
        
    try:
        await manager.broadcast_disconnect_room(
            room_id, 
            {"type": "system", "content": f"Chatroom has been deleted by user {user_id}"}
        )
    except Exception:
        pass

    return {"message": f"Chatroom (ID: {room_id}) has been successfully deleted by its member"}

@app.websocket("/WebSocket/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str = Query(...)) -> None:
    try:
        token_string = token.split(" ")[1] if " " in token else token
        payload = JWTTool.verify_token(token_string)
        user_id = payload.get("user_id")

    except Exception:
        raise HTTPException(401, "Invalid token or expired")
    
    await manager.connect(room_id, user_id, websocket)

    await set_user_online(user_id)

    history_messages = await get_messages_by_room(room_id, limit = 50) 
    
    await websocket.send_text(json.dumps({
        "type": "history",
        "data": history_messages
    }))

    sequence = 0
    try:
        while True:
            data = await websocket.receive_text()  # 等待並接收前端傳來的文字訊息
            packet = json.loads(data)
            packet_type = packet.get("type")

            # 心跳機制
            if packet_type == "ping":
                await websocket.send_text(
                    json.dumps({
                        "type": "pong"
                    })
                )

                continue

            # 聊天訊息
            if packet_type == "message":
                sequence += 1
                content = packet["content"]  # 撈出聊天文字

                await insert_message(room_id, user_id, sequence, content)

                message = {
                    "type": "message",
                    "sequence": sequence,
                    "sender_id": user_id,
                    "content": content
                }

                await manager.broadcast(room_id, message)

                await websocket.send_text(
                    json.dumps({
                        "type": "ack",
                        "seq": sequence
                    })
                )
            
            if packet_type == "read":
                sequence_id = packet["sequence"]

                await mark_message_as_read(user_id, sequence_id)

                await manager.broadcast(
                    room_id,
                    {
                        "type": "read",
                        "sequence": sequence_id,
                        "user_id": user_id
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id)
        set_user_offlined(user_id)