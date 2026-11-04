let currentRoom = "";
let currentPlayer = "";
let isHost = false;
let galleryPhotos = [];
let galleryIndex = 0;

const socket = io();
console.log("JS LOADED");

async function joinGame() {
    const player =
        document.getElementById("name").value;
    const room =
        document.getElementById("room").value.toUpperCase();
    const response =
        await fetch("/join", {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify({
                room,
                player
            })
        });
    const data = await response.json();
    isHost = data.host === player;
    currentPlayer = player;
    currentRoom = room;
    localStorage.setItem("player",player);
    localStorage.setItem("room",room);

    document.getElementById("claim-bingo").style.display = "block";
    document.getElementById("leave-game").style.display = "block";
    document.getElementById("current-room-code").textContent = room;
    document.getElementById("room-banner").style.display = "block";

    drawBoard(data.board);
    restoreBoard(data.completed, data.photos);

    socket.emit("join_room", {player: player, room: room});
    setTimeout(async () => {
    const response = await fetch(`/players?room=${room}`);
    const data = await response.json();
    const playersDiv = document.getElementById("players");
    playersDiv.innerHTML = "";
    data.players.forEach(name => {
        const div = document.createElement("div");
        div.className = "player";
        div.textContent = name;
        playersDiv.appendChild(div);
    });

}, 500);
}

socket.on("message", (data) => {
    const msg =
        document.createElement("div");
    msg.textContent =
        data.text;
    document
        .getElementById("messages")
        .appendChild(msg);
});

socket.on("player_list", (data) => {
    const playersDiv = document.getElementById("players");
    playersDiv.innerHTML = "";
    data.players.forEach(player => {
        const div = document.createElement("div");
        div.className = "player";
        div.textContent = player;
        playersDiv.appendChild(div);
    });
});

socket.on("bingo_claimed", (data) => {
    console.log("BINGO CLAIM RECEIVED", data);
    if (!isHost) return;
    document.getElementById("review-player").textContent =
        `${data.player} is claiming BINGO`;
    document.getElementById("review-image").src =
        data.image + "?t=" + Date.now();
    document.getElementById("review-panel").style.display =
        "block";
});

socket.on("bingo_denied", (data) => {
    if (data.player === currentPlayer) {
        alert("Bingo denied. Your board has been reset.");
        drawBoard(data.board);
    } else {
        alert(`${data.player}'s bingo claim was denied.`);
    }
    document.getElementById("review-image").src = "";
    document.getElementById("review-player").textContent = "";
    document.getElementById("review-panel").style.display = "none";
});

socket.on("bingo_approved", (data) => {
    document.getElementById("board").style.display = "none";
    document.getElementById("gallery-screen").style.display = "block";
    document.getElementById("winner-name").textContent =
        `${data.winner} Wins!`;
    galleryPhotos = data.gallery;
    galleryIndex = 0;
    showPhoto();
    document.getElementById("review-image").src = "";
    document.getElementById("review-player").textContent = "";
    document.getElementById("review-panel").style.display = "none";
});

async function createGame() {
    const player =
        document.getElementById("name").value;
    const response =
        await fetch("/create", {
            method: "POST",
            headers: {
                "Content-Type":"application/json"
            },
            body: JSON.stringify({
                player: player
            })
        });
    const data = await response.json();
    document.getElementById("room").value = data.room;
    document.getElementById("current-room-code").textContent = data.room;
    document.getElementById("room-banner").style.display = "block";
    await joinGame();
}
function showRules() {
    document.getElementById("rules-screen").style.display = "block";
}

function hideRules() {
    document.getElementById("rules-screen").style.display = "none";
}
function drawBoard(board) {
    const boardDiv =
        document.getElementById("board");
    boardDiv.innerHTML = "";
    const headers = ["S", "E", "M", "A"];
    headers.forEach(letter => {
        const header =
            document.createElement("div");
        header.className = "header";
        header.innerText = letter;
        boardDiv.appendChild(header);
    });
    board.flat().forEach(prompt => {
        const button =
            document.createElement("button");
        button.className = "square";
        button.innerText = prompt;
        button.onclick = () => {
            openCamera(prompt, button);
        };
        boardDiv.appendChild(button);
    });
}

function restoreBoard(completed, photos) {
    document.querySelectorAll(".square").forEach(button => {
        const prompt = button.innerText;
        if (!completed.includes(prompt)) {
            return;
        }
        const photo = photos[prompt];
        if (!photo) {
            return;
        }
        completeSquare(
            button,
            prompt,
            photo.url
        );
    });
}

async function openCamera(prompt, button) {
    const input =
        document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.capture = "environment";
    input.click();
    input.onchange = async () => {
        const photo = input.files[0];
        if (!photo) return;
        const formData =
            new FormData();
        formData.append("photo",photo);
        formData.append("prompt",prompt);
        formData.append("player",currentPlayer);
        formData.append("room",currentRoom);
        const response =
            await fetch(
                "/upload",
                {
                    method: "POST",
                    body: formData
                }
            );
        const data =
            await response.json();
        completeSquare(
            button,
            prompt,
            data.photo_url
        );
    };
}

function completeSquare(button, prompt, imageUrl) {
    button.style.backgroundImage = `url(${imageUrl})`;
    button.style.backgroundSize = "cover";
    button.style.backgroundPosition = "center";
    button.innerHTML =
        `<div class="square-label">${prompt}</div>`;
    button.classList.add("completed");
}

async function leaveGame() {
    if (!currentRoom) {
        return;
    }
    await fetch("/leave", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            room: currentRoom,
            player: currentPlayer
        })
    });
    currentRoom = "";
    currentPlayer = "";
    document.getElementById("board").innerHTML = "";
    document.getElementById("claim-bingo").style.display = "none";
    document.getElementById("leave-game").style.display = "none";
    document.getElementById("room").value = "";
    document.getElementById("room-banner").style.display = "none";
    alert("You left the game.");
}

async function claimBingo() {
    alert("Submitting board for review...");
    const board = document.getElementById("board");
    const canvas = await html2canvas(board);
    canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append("board", blob, "board.png");
        formData.append("player", currentPlayer);
        formData.append("room", currentRoom);
        const response = await fetch("/claim_bingo", {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            alert("Bingo claim sent to host.");
        } else {
            alert("Failed to submit bingo.");
        }
    });
}

async function approveBingo() {
    await fetch("/approve_bingo", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            room: currentRoom
        })
    });
    document.getElementById("review-panel").style.display = "none";
}

async function denyBingo() {
    await fetch("/deny_bingo", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            room: currentRoom
        })
    });
    document.getElementById("review-panel").style.display = "none";
}

function showPhoto() {
    if (galleryPhotos.length === 0) return;
    const photo = galleryPhotos[galleryIndex];
    document.getElementById("gallery-image").src =
        photo.url;
    document.getElementById("gallery-caption").textContent =
        `${photo.prompt} - ${photo.player}`;
    document.getElementById("download-photo").onclick =
        () => {
            const link = document.createElement("a");
            link.href = photo.url;
            link.download = "";
            link.click();
        };
}

function nextPhoto() {
    galleryIndex++;
    if (galleryIndex >= galleryPhotos.length) {
        galleryIndex = 0;
    }
    showPhoto();
}

function prevPhoto() {
    galleryIndex--;
    if (galleryIndex < 0) {
        galleryIndex = galleryPhotos.length - 1;
    }
    showPhoto();
}

function downloadMyPhotos() {
    window.location.href =
        `/download_photos?room=${currentRoom}&player=${currentPlayer}`;
}

window.onload = async () => {
    const player = localStorage.getItem("player");
    const room = localStorage.getItem("room");
    if (!player || !room) return;
    document.getElementById("name").value = player;
    document.getElementById("room").value = room;
    await joinGame();
};
