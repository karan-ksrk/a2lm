from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="your-personal-gateway-key"
)

# Test 1: basic
resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(resp.choices[0].message.content)

# Test 2: streaming
for chunk in client.chat.completions.create(
    model="fast",
    messages=[{"role": "user", "content": "Count to 5"}],
    stream=True
):
    print(chunk.choices[0].delta.content or "", end="", flush=True)

# Test 3: test fallback — exhaust groq by calling 30+ times fast
# The gateway should silently switch to openrouter/google
