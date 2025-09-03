import React, { useState, useEffect } from "react";

function App() {
  const [polls, setPolls] = useState([]);
  const [selectedPoll, setSelectedPoll] = useState(null);
  const [results, setResults] = useState([]);
  const [ws, setWs] = useState(null);

  // Form state for new poll
  const [title, setTitle] = useState("");
  const [question, setQuestion] = useState("");
  const [choices, setChoices] = useState(["", ""]);

  // Load polls
  useEffect(() => {
    fetchPolls();
  }, []);

  const fetchPolls = () => {
    fetch("http://127.0.0.1:8000/polls")
      .then(res => res.json())
      .then(data => setPolls(data));
  };

  // Connect websocket when poll is selected
  useEffect(() => {
    if (!selectedPoll) return;

    const socket = new WebSocket(`ws://127.0.0.1:8000/polls/ws/${selectedPoll.id}`);
    socket.onopen = () => {
      console.log("WebSocket connected");
      setResults([]); // reset results on new connection
    };
    socket.onmessage = event => {
      const data = JSON.parse(event.data);
      console.log("WebSocket message:", data);
      if (data.data && data.data.results)
        setResults(data.data.results);
    };
    socket.onclose = () => console.log("WebSocket closed");
    setWs(socket);

    return () => {
      socket.close();
    };
  }, [selectedPoll]);

  const handleVote = async choiceId => {
    await fetch(`http://127.0.0.1:8000/polls/${selectedPoll.id}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ choice_id: choiceId, username: window.crypto.randomUUID() }) // static username for now
    });
  };

  const handleAddChoice = () => {
    setChoices([...choices, ""]);
  };
  const handleDeleteChoice = () => {
    setChoices(choices.slice(0, -1));
  };

  const handleChoiceChange = (index, value) => {
    const newChoices = [...choices];
    newChoices[index] = value;
    setChoices(newChoices);
  };

  const handleCreatePoll = async () => {
    if (!title || !question || choices.some(c => !c)) {
      alert("Please fill out all fields");
      return;
    }

    await fetch("http://127.0.0.1:8000/polls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        question,
        choices: choices.map(text => ({ text }))
      })
    });

    setTitle("");
    setQuestion("");
    setChoices(["", ""]);
    fetchPolls();
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>Poll App</h1>

      {!selectedPoll && (
        <>
          <h2>Create Poll</h2>
          <input
            placeholder="Title"
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
          <br />
          <input
            placeholder="Question"
            value={question}
            onChange={e => setQuestion(e.target.value)}
          />
          <br />
          {choices.map((c, i) => (
            <div key={i}>
              <input
                placeholder={`Choice ${i + 1}`}
                value={c}
                onChange={e => handleChoiceChange(i, e.target.value)}
              />
            </div>
          ))}
          <button onClick={handleAddChoice}>Add Choice</button>
          <br/>
          <button onClick={handleDeleteChoice} disabled={choices.length <= 2}>Delete Choice</button>
          <br />
          <button onClick={handleCreatePoll}>Create Poll</button>

          <h2>Available Polls</h2>
          <ul>
            {polls.map(p => (
              <li key={p.id}>
                {p.title} - {p.question}{" "}
                <button onClick={() => setSelectedPoll(p)}>Open</button>
              </li>
            ))}
          </ul>
        </>
      )}

      {selectedPoll && (
        <>
          <h2>{selectedPoll.title}</h2>
          <p>{selectedPoll.question}</p>
          <ul>
            {selectedPoll.choices.map(c => (
              <li key={c.id}>
                {c.text}{" "}
                <button onClick={() => handleVote(c.id)}>Vote</button>
              </li>
            ))}
          </ul>

          <h3>Live Results</h3>
         <ul>
            {results.map(r => (
                <li key={r.id}>
                Choice {r.text}: {r.votes} votes
                </li>
            ))}
         </ul>

          <button onClick={() => setSelectedPoll(null)}>Back</button>
        </>
      )}
    </div>
  );
}

export default App;
