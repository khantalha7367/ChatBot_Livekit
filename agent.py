import logging
import asyncio
from typing import Annotated
from time import perf_counter,sleep
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    tokenize
)
from livekit.agents.pipeline import VoicePipelineAgent,AgentTranscriptionOptions
from livekit.plugins import openai, silero  #, turn_detector
from livekit.agents import metrics

from stt_custom import STT
from tts_custom import LocalTTS

from livekit.agents.tts import StreamAdapter
import random

data = {
    "Dr. John Smith": {
        "appointments": [
            {"time": "9:00 AM", "status": "booked"},
            {"time": "10:30 AM", "status": "free"},
            {"time": "1:00 PM", "status": "booked"},
        ]
    },
    "Dr. Sarah Lee": {
        "appointments": [
            {"time": "9:15 AM", "status": "free"},
            {"time": "11:00 AM", "status": "booked"},
            {"time": "2:00 PM", "status": "free"},
        ]
    },
    "Dr. Emily Harris": {
        "appointments": [
            {"time": "8:45 AM", "status": "booked"},
            {"time": "10:15 AM", "status": "booked"},
            {"time": "12:45 PM", "status": "free"},
        ]
    },
}

hospitals = {
    'indus hospital':{
        "Facilities":[
            {'MRI':'Available'},
            {'Diabetes Screening':'Not Available'}
        ]
    },

    'rmi hospital':{
        "Facilities":[
            {'MRI':'Available'},
            {'Diabetes Screening':'Available'}
        ]
    },

    'park hospital':{
        "Facilities":[
            {'MRI':'Not Available'},
            {'Diabetes Screening':'Available'}
        ]
    }
}



function_time_end,function_time_start=0,0
agent_chat_commit = 0
usage_collector = metrics.UsageCollector()
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")




def prewarm(proc: JobProcess):
   
    proc.userdata["vad"] = silero.VAD.load()




class AssistantFnc(llm.FunctionContext):
    @llm.ai_callable()
    async def get_appointments(
        self,
        doctor_name: Annotated[str, llm.TypeInfo(description="The doctor’s name")],
    ):
        """
        Called when the user asks about a doctor’s availability or appointments.
        This function returns a dictionary containing all appointment times and
        statuses for the given doctor.
        """

        doctor_name_key = doctor_name.strip()
        return data.get(doctor_name_key, {"error": f"No data found for {doctor_name_key}."})
        # if doctor_name_key in data:
        #     return data[doctor_name_key]
        # else:
        #     return {"error": f"No data found for doctor {doctor_name_key}."}
        
    @llm.ai_callable()
    async def get_hospitals(
        self,
        hospital_name: Annotated[str, llm.TypeInfo(description="The hospital's name")],
    ):
        """
        Called when the user asks about a hospital availability or services.
        This function returns a dictionary containing all facilities and
        statuses for the given hospital.
        """

        hospital_name_key = hospital_name.strip().lower()
        return hospitals.get(hospital_name_key, {"error": f"No data found for {hospital_name_key}."})
        # if hospital_name_key in hospitals:
        #     return hospitals[hospital_name_key]
        # else:
        #     return {"error": f"No data found for hospital {hospital_name_key}."}




async def log_usage():
    summary = usage_collector.get_summary()
    logger.info(f"Usage: ${summary}")



# async def add_user_context(assistant: VoicePipelineAgent, chat_ctx: llm.ChatContext):
   
#     # if not chat_ctx.messages:
        
#     #     chat_ctx.append(
#     #         role="system",
#     #         text="Additional context about user preferences could be added here"
#     #     )
   
#     user_messages = [msg for msg in chat_ctx.messages if msg.role == "user"]
#     if user_messages:
#         latest_user_msg = user_messages[-1]
#         chat_ctx.append(
#             role="system",
#             text=f"User recently mentioned: {latest_user_msg.text[:50]}..."
#         )


async def say_wait(agent: VoicePipelineAgent):
    msgs = ["Let me find that for you","I'll check that for you",
            "Please hold for a second","Let me get that for you"]
    ans = random.choice(msgs)
    await agent.say(ans, allow_interruptions=True)
    await asyncio.sleep(0.2)


async def entrypoint(ctx: JobContext):
    logger.info(f"Connecting to room: {ctx.room.name}")
    
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit. You have access to a function "
            "called 'get_appointments(doctor_name)' that returns all the appointment times "
            "and statuses for that doctor. You also have access to a function "
            "called 'get_hospitals(hospital_name)' that returns all the hospitals facilities "
            "and statuses for their availibility."
            "Keep your responses short, helpful, and voiced-friendly."
        ),
    )

    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant connected: {participant.identity}")

    fnc_ctx = AssistantFnc()

    local_tts = openai.TTS() #LocalTTS()

    tts = StreamAdapter(tts=local_tts,sentence_tokenizer=tokenize.basic.SentenceTokenizer(),)

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt= openai.STT(),#STT(vad=ctx.proc.userdata["vad"]),   #openai.STT(),                
        llm= openai.LLM(model="gpt-4o-mini",parallel_tool_calls=True,temperature=0),   #.with_groq(),   #(model="gpt-4o-mini",parallel_tool_calls=True,temperature=0),
        tts= tts,     #LocalTTS(),           #openai.TTS(),
        #turn_detector=turn_detector.EOUModel,
        chat_ctx=initial_ctx,
        fnc_ctx=fnc_ctx,                         
        max_endpointing_delay=0.01,
        allow_interruptions=True,
        interrupt_speech_duration=0.5,
        max_nested_fnc_calls=2,
        preemptive_synthesis=True,
        #transcription=AgentTranscriptionOptions(sentence_tokenizer=tokenize.basic.SentenceTokenizer()),
    )   

    #ctx.add_shutdown_callback(log_usage)
    
    #wss://assistant-jo4vzvy6.livekit.cloud

    @agent.on('user_stopped_speaking')
    def on_user_stopped_speaking():
        global function_time_start
        #print("User has spoken")
        function_time_start = perf_counter()

    # @agent.on('user_speech_committed')
    # def on_agent_speech_committed():
    #     global agent_chat_commit
    #     #print("User has spoken")
    #     agent_chat_commit = perf_counter()

    #     #total = user_chat_commit - function_time_start

    #     #print(f"STT time:{total}")

    @agent.on("function_calls_collected")
    def on_function_calls_collected():
        # global agent_chat_commit
        # #print("User has spoken")
        # function_call_finished = time()
        # total = function_call_finished - agent_chat_commit
        # print(f"LLM Time: {total}")
        asyncio.create_task(say_wait(agent=agent))
        #await agent.say("Let me find that for you", allow_interruptions=True)

    
    @agent.on('agent_started_speaking')
    def on_agent_started_speaking():
        global function_time_start
        function_time_end = perf_counter()

        # print(f"start time:{function_time_start}")
        # print(f"end time:{function_time_end}")

        total = function_time_end-function_time_start
        #total_latency = eou.end_of_utterance_delay + llm.ttft + tts.ttfb
        print(f"Total function time: {total}")


    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        # Use this helper to format and log based on metrics type
        metrics.log_metrics(mtrcs)

    agent.start(ctx.room, participant)

    await agent.say("Hello, how can I help you today?", allow_interruptions=True)



if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
