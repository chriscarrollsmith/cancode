const root = document.getElementById("gameRoot");
if (root) {
  const playerId = root.dataset.playerId || null;
  const ui = {
    statusMessage: document.getElementById("statusMessage"),
    phaseLabel: document.getElementById("phaseLabel"),
    promptText: document.getElementById("promptText"),
    timer: document.getElementById("timer"),
    answerForm: document.getElementById("answerForm"),
    answerInput: document.getElementById("answerInput"),
    answers: document.getElementById("answers"),
    waitingNote: document.getElementById("waitingNote"),
    winnerBanner: document.getElementById("winnerBanner"),
    playerList: document.getElementById("playerList"),
    metaLine: document.getElementById("metaLine"),
  };

  let state = null;
  let lastPrompt = "";
  let socket = null;
  let timerHandle = null;
  let heartbeatStarted = false;

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${proto}://${location.host}/ws`);

    socket.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "pong") return;
      render(data);
    });

    socket.addEventListener("close", () => {
      window.setTimeout(connect, 1000);
    });

    if (!heartbeatStarted) {
      heartbeatStarted = true;
      window.setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "ping" }));
        }
      }, 15000);
    }
  }

  function send(payload) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    }
  }

  function render(next) {
    state = next;
    ui.statusMessage.textContent = next.status_message;
    ui.phaseLabel.textContent = prettyPhase(next.phase);

    const prompt =
      next.prompt_text || "Waiter, there's a _____ in my soup!";
    if (prompt !== lastPrompt) {
      ui.promptText.textContent = prompt;
      ui.promptText.classList.remove("is-fresh");
      void ui.promptText.offsetWidth;
      ui.promptText.classList.add("is-fresh");
      lastPrompt = prompt;
    }

    renderTimer(next.phase_ends_at);
    renderPlayers(next);
    renderPlayArea(next);
  }

  function prettyPhase(phase) {
    switch (phase) {
      case "lobby":
        return "Lobby";
      case "answering":
        return "Answer time";
      case "voting":
        return "Voting";
      case "results":
        return "Winner";
      default:
        return phase;
    }
  }

  function renderTimer(endsAt) {
    if (timerHandle) {
      window.clearInterval(timerHandle);
      timerHandle = null;
    }
    if (!endsAt) {
      ui.timer.hidden = true;
      return;
    }
    const tick = () => {
      const remaining = Math.max(0, Math.ceil(endsAt - Date.now() / 1000));
      ui.timer.hidden = false;
      ui.timer.textContent = `${remaining}s`;
    };
    tick();
    timerHandle = window.setInterval(tick, 200);
  }

  function renderPlayers(next) {
    ui.playerList.replaceChildren(
      ...next.players.map((player) => {
        const li = document.createElement("li");
        if (player.is_active) li.classList.add("is-active");
        if (!player.connected) li.classList.add("is-away");
        const name = document.createElement("span");
        name.textContent =
          player.id === playerId ? `${player.name} (you)` : player.name;
        const score = document.createElement("span");
        score.className = "score";
        score.textContent = String(player.score);
        li.append(name, score);
        return li;
      }),
    );
    ui.metaLine.textContent =
      next.phase === "lobby"
        ? `${next.connected_count}/${next.min_players} needed to start`
        : `Round ${next.round_number} · ${next.connected_count} at the table`;
  }

  function renderPlayArea(next) {
    ui.answerForm.hidden = true;
    ui.answers.hidden = true;
    ui.waitingNote.hidden = true;
    ui.winnerBanner.hidden = true;
    ui.answers.replaceChildren();

    if (next.phase === "answering") {
      if (next.my_role === "player" && !next.has_submitted_answer) {
        ui.answerForm.hidden = false;
      } else if (next.my_role === "player") {
        ui.waitingNote.hidden = false;
        ui.waitingNote.textContent = "Answer in! Waiting for the other player…";
      } else {
        ui.waitingNote.hidden = false;
        ui.waitingNote.textContent = "Players are cooking up answers…";
      }
      return;
    }

    if (next.phase === "voting" || next.phase === "results") {
      ui.answers.hidden = false;
      for (const answer of next.answers) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "answer";
        btn.dataset.target = answer.player_id;

        const name = document.createElement("span");
        name.className = "answer__name";
        name.textContent =
          next.phase === "results" ? answer.player_name : "Anonymous ladle";

        const text = document.createElement("span");
        text.className = "answer__text";
        text.textContent = answer.text;
        btn.append(name, text);

        if (next.phase === "results" && answer.vote_count != null) {
          const votes = document.createElement("span");
          votes.className = "answer__votes";
          votes.textContent = `${answer.vote_count} vote${
            answer.vote_count === 1 ? "" : "s"
          }`;
          btn.append(votes);
        }

        const canVote =
          next.phase === "voting" &&
          next.my_role === "voter" &&
          !next.has_voted;
        if (!canVote) {
          btn.disabled = true;
        } else {
          btn.addEventListener("click", () => {
            send({ type: "vote", target_player_id: answer.player_id });
          });
        }
        if (next.has_voted && next.my_role === "voter") {
          // Selection feedback is approximate; server is source of truth.
        }
        ui.answers.append(btn);
      }

      if (next.phase === "voting") {
        if (next.my_role === "player") {
          ui.waitingNote.hidden = false;
          ui.waitingNote.textContent = "Your answer is up. Waiting for votes…";
        } else if (next.has_voted) {
          ui.waitingNote.hidden = false;
          ui.waitingNote.textContent = "Vote cast. Waiting for everyone else…";
        }
      }
    }

    if (next.phase === "results") {
      ui.winnerBanner.hidden = false;
      if (next.winner_names.length === 0) {
        ui.winnerBanner.textContent = "No winner this round.";
      } else if (next.winner_names.length === 1) {
        ui.winnerBanner.textContent = `${next.winner_names[0]} takes the bowl!`;
      } else {
        ui.winnerBanner.textContent = `Tie! ${next.winner_names.join(" & ")} share the crown.`;
      }
    }

    if (next.phase === "lobby") {
      ui.waitingNote.hidden = false;
      ui.waitingNote.textContent = next.status_message;
    }
  }

  ui.answerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = ui.answerInput.value.trim();
    if (!text) return;
    send({ type: "answer", text });
    ui.answerInput.value = "";
  });

  connect();
}
