import base64

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

def query_recycle_method_from_image(image_bytes:bytes, city_or_region:str)->str:
    print("identify_object_in_image enter")
    llm = ChatOpenAI(
        model="gpt-4o-2024-08-06",
        temperature=0.5,
    )
    with open(f"./data/{city_or_region}-summary.txt", "r", encoding="utf-8") as file:
        instruction = file.read()
    image_b64 = base64.b64encode(image_bytes).decode()
    prompt = (f"identify one major object in this image, then use the dispose/collection instruction: {instruction}."
              "suggest best way to dispose major object as garbage, example: green bin, blue box, regular garbage bag, paper yark bag, drop off at depot."
              "if required to drop off of at Recycling Depots & Drop Off Centres, give address, contact and hours."
              )
    message = HumanMessage(
        content=[
            # {"type": "text", "text": "identify one major object in this image, "
            #                          "output object name material and category in one line with comma separated"},
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            },
        ],
    )
    response = llm.invoke([message])
    return response.content

def create_llm_model():
    llm = init_chat_model("llama-3.3-70b-versatile", model_provider="groq")
    return llm

def query_dispose_instruction(city_or_region:str, desc:str):
    with open(f"./data/{city_or_region}-summary.txt", "r", encoding="utf-8") as file:
        inst = file.read()
    prompt = (f"given below garbage description: {desc} and dispose/collection instruction: {inst}."
              "suggest best way to dispose this garbage, example: green bin, blue box, regular garbage bag, paper yark bag, drop off at depot."
              "if required to drop off of at Recycling Depots & Drop Off Centres, give address, contact and hours."
              )
    resp = create_llm_model().invoke(prompt)
    return resp.content

# with open("./data/cup2.jpg", "rb") as file:
#     image_bytes = file.read()
# print(identify_object_in_image(image_bytes))


