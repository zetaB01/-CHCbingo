from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_socketio import SocketIO, emit, join_room
import random
import string
import os
import uuid
import zipfile


app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

print("Bingo server started")

PROMPTS = [
    "Burning Ashtray",
    "Swag Hoarder",
    "Just Underpants",
    "Booth Bunny wearing sneakers",
    "1948 Relic Blue F1",
    "Sitting on the floor eating",
    "More drinks than hands",
    "A mullet",
    "TP on foot",
    "Spiked Hair Visor",
    "Sleeping in hallway",
    "Scott Stutler",
    "Clearly not a service dog",
    "Pajamas",
    "Face tattoo",
    "Overflowing garbage can",
    "3 inch or taller heels",
    "Man-bun",
    "Neck tattoo",
    "Milwaukee Brewers shirt",
    "Green bay packers shirt",
    "Long line at the Ladies Restroom",
    "Empty garbage can",
    "Rat tail hair",
    "Tallest Side by Side",
    "Airbrushed mural (NOT vinyl)",
    "Purse dog",
    "Oversized cocktail before 10am",
    "Barefoot", 
    "Scooter drag racing",
    "Graffiti",
    "Visable Ass Crack",
    "Bald Man with long hair",
    "Wet hair sign",
    "Too young to be on a scooter",
    "Elvis",
    "Skin-colored bodysuit", 
    "Thrush bird",
    "Engineering Crazy",
    "Sock footed person",
    "Weirdest unneccessary vehicle upgrade",
    "Comb over",
    "Radically colored hair",
    "Booth with flowers",
    "Grass floor",
    "Escalator closed sign",
    "First time at SEMA",
    "N/A SBC",
    "LS Swapped Ford",
    "Coyote swapped Chevy",
    "Out Of Order Restroom",
    "Collect a free Pen",
    "Spin to Win ___",
    "Ghost Booth",
    "Wall outlet squatter",
    "Invisable Driveshaft",
    "Trashcan as a table",
    "Unmanned Info Booth",
    "Dual phone holster",
    "Box as a backpack",
    "Swag hat stack",
    "Standing napper",
    "Roller Skates",
    "Rotary motor",
    "Delorian with a flux capacitor",
    "Too many turbos",
    "Fuzzy Wnidow Dice"
]

games = {}

def generate_board():
    prompts = random.sample(PROMPTS, 16)
    board = []
    for i in range(4):
        board.append(
            prompts[i*4:(i+1)*4])
    return board

def make_room_code():
    return ''.join(
        random.choices(
            string.ascii_uppercase +
            string.digits,
            k=6))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/create", methods=["POST"])
def create_room():
    data = request.json
    host_name = data["player"]
    room = make_room_code()
    games[room] = {
        "host": host_name,
        "state": "playing",
        "players": {},
        "pending_bingo": None,
    }
    print("Game created:", room)
    print(games)
    return {
        "room": room
    }

@app.route("/join", methods=["POST"])
def join():
    data = request.json
    room = data["room"].upper()
    player = data["player"]
    if player in games[room]["players"]:
        board = games[room]["players"][player]["board"]
    else:
        board = generate_board()
        games[room]["players"][player] = {
            "board": board,
            "completed": [],
            "photos": {}
        }
    return {"board": board, "host": games[room]["host"], "completed": games[room]["players"][player]["completed"], "photos": 
            games[room]["players"][player]["photos"]}

@socketio.on("join_room")
def handle_join(data):
    room = data["room"].upper()
    join_room(room)
    emit("message", {
        "text": f'{data["player"]} joined'
    }, room=room)
    socketio.emit("player_list", {
        "players": list(games[room]["players"].keys())
    }, room=room)

@app.route("/upload", methods=["POST"])
def upload():
    photo = request.files["photo"]
    prompt = request.form["prompt"]
    player = request.form["player"]
    room = request.form["room"]
    filename = f"{uuid.uuid4()}.jpg"
    path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )
    photo.save(path)
    photo_url = f"/uploads/{filename}"
    games[room]["players"][player]["photos"][prompt] = {
        "url": photo_url, 
        "path": path
    }
    games[room]["players"][player]["completed"].append(prompt)
    return jsonify({
        "success": True,
        "photo_url": photo_url
    })

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

@app.route("/leave", methods=["POST"])
def leave():
    data = request.json
    room = data["room"]
    player = data["player"]
    if room in games:
        games[room]["players"].pop(player, None)
        socketio.emit("player_list", {"players": list(games[room]["players"].keys())}, room=room)
        print(f"{player} left {room}")
        socketio.emit("message",{"text":f"{player} left the room"},room=room)
    if not games[room]["players"]:
        del games[room]
        print(f"{room} deleted")
    return {"success": True}

@app.route("/claim_bingo", methods=["POST"])
def claim_bingo():
    room = request.form["room"]
    player = request.form["player"]
    image = request.files["board"]
    filename = f"{room}_{player}.png"
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    image.save(path)
    image_url = f"/uploads/{filename}"
    games[room]["pending_bingo"] = {
        "player": player,
        "image": image_url
    }
    socketio.emit("bingo_claimed", {
        "player": player,
        "image": image_url
    }, room=room)
    return {"success": True}

@app.route("/approve_bingo", methods=["POST"])
def approve_bingo():
    room = request.json["room"]
    winner = games[room]["pending_bingo"]["player"]
    gallery = []
    for player_name, player_data in games[room]["players"].items():
        for prompt, photo_data in player_data["photos"].items():
            gallery.append({
                "player": player_name,
                "prompt": prompt,
                "url": photo_data["url"]
            })
    socketio.emit("bingo_approved", {
        "winner": winner,
        "gallery": gallery
    })
    games[room]["state"] = "finished"
    games[room]["pending_bingo"] = None
    return {"success": True}

@app.route("/deny_bingo", methods=["POST"])
def deny_bingo():
    room = request.json["room"]
    player = games[room]["pending_bingo"]["player"]
    photos = games[room]["players"][player]["photos"]
    # Delete claim screenshot
    claim_image = games[room]["pending_bingo"]["image"]
    claim_path = claim_image.replace("/uploads/", "uploads/")
    if os.path.exists(claim_path):
        os.remove(claim_path)
        print("Deleted claim image:", claim_path)
    # Delete all uploaded square photos
    for photo_data in photos.values():
        file_path = photo_data.get("path")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print("Deleted photo:", file_path)
    # Generate fresh board
    new_board = generate_board()
    games[room]["players"][player] = {
        "board": new_board,
        "completed": [],
        "photos": {}
    }
    games[room]["pending_bingo"] = None
    socketio.emit("bingo_denied", {
        "player": player,
        "board": new_board
    })
    return {"success": True}

@app.route("/download_photos")
def download_photos():
    room = request.args["room"]
    player = request.args["player"]
    player_data = games[room]["players"][player]
    zip_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        f"{player}_photos.zip"
    )
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for prompt, photo_data in player_data["photos"].items():
            photo_path = photo_data["path"]
            if os.path.exists(photo_path):
                extension = os.path.splitext(photo_path)[1]
                safe_name = prompt.replace("/", "-")
                zipf.write(
                    photo_path,
                    arcname=f"{safe_name}{extension}"
                )
    return send_file(
        zip_path,
        as_attachment=True
    )

@app.route("/players")
def players():
    room = request.args["room"]
    return {
        "players": list(games[room]["players"].keys())
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app,host="0.0.0.0",port=port, allow_unsafe_werkzeug=True)
