import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    url = os.getenv("EVOLUTION_API_URL")
    key = os.getenv("EVOLUTION_API_KEY")
    
    print(f"Testando conexão com: {url}")
    print(f"Usando chave: {key[:10]}...{key[-5:]}")
    
    headers = {"apikey": key}
    
    try:
        async with httpx.AsyncClient() as client:
            # Tentar buscar instâncias
            resp = await client.get(f"{url}/instance/fetchInstances", headers=headers)
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {resp.text}")
            
    except Exception as e:
        print(f"Erro: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection())
