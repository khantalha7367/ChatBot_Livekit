This repo is an edited and enhanced version of the Livekit Voice-to-Voice Agent. It is a sample app that has a built-in functions with local data structures to simulate a doctors appointment assistant. Built-in LveKit Events have been used to fill up any awkward silences.
To run this app, you would need a livekit account, alongwith an OpenAI or some other AI service API. AI providers supported can be found in the documentation. 
Furthermore, you need to install the livekit CLI to work with this project and understand its room based architecture
This project also uses custom TTS and STT classes in order to make sure the responses are streamed and thus work faster. Developers are welcome to clone and develop this project further.

NOTE: This project is not enterprise tested

# Python Voice Agent

<p>
  <a href="https://cloud.livekit.io/projects/p_/sandbox"><strong>Deploy a sandbox app</strong></a>
  •
  <a href="https://docs.livekit.io/agents/overview/">LiveKit Agents Docs</a>
  •
  <a href="https://livekit.io/cloud">LiveKit Cloud</a>
  •
  <a href="https://blog.livekit.io/">Blog</a>
</p>

A basic example of a voice agent using LiveKit and Python.

## Dev Setup

Clone the repository and install dependencies to a virtual environment:

```console
cd voice-pipeline-agent-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set up the environment by filling in the required values in `.env.local`:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`

You can also do this automatically using the LiveKit CLI:

```console
lk app env
```

Run the agent:

```console
python3 agent.py dev
```

This agent requires a frontend application to communicate with. You can use one of our example frontends in [livekit-examples](https://github.com/livekit-examples/), create your own following one of our [client quickstarts](https://docs.livekit.io/realtime/quickstarts/), or test instantly against one of our hosted [Sandbox](https://cloud.livekit.io/projects/p_/sandbox) frontends.
