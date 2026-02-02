import asyncio
import os
from dotenv import load_dotenv
from app.services.whatsapp.providers.evolution import EvolutionProvider
from app.services.whatsapp.models import InstanceConfig

# Carregar variáveis de ambiente
load_dotenv()

async def run_smoke_test():
    """
    Script de teste rápido para criar uma instância na Evolution
    e validar a ponte com o Chatwoot.
    """
    print("Iniciando Smoke Test: Evolution + Chatwoot Bridge")
    
    api_url = os.getenv("EVOLUTION_API_URL")
    api_key = os.getenv("EVOLUTION_API_KEY")
    
    if not api_url or not api_key:
        print("Erro: EVOLUTION_API_URL ou EVOLUTION_API_KEY não configurados no .env")
        return

    provider = EvolutionProvider(api_url=api_url, api_key=api_key)
    
    test_instance_name = "test-agent-slim"

    try:
        print(f"Buscando QR Code para a instancia '{test_instance_name}'...")
        qr = await provider.get_qr_code(test_instance_name)
        
        if qr:
            print("\n" + "="*50)
            print("SUCESSO! QR CODE OBTIDO")
            print("="*50)
            print(f"\nBase64 do QR Code (copie e use em um site de Base64 to Image se necessario):")
            
            # Print in chunks to avoid truncation
            code = qr.code
            chunk_size = 1000
            for i in range(0, len(code), chunk_size):
                print(code[i:i+chunk_size])
                
            print("\n" + "="*50)
            print("PROXIMO PASSO:")
            print("1. Escaneie este QR Code no seu WhatsApp.")
            print("2. Assim que conectar, mande um 'Oi'.")
            print("3. O sistema deve responder no Chatwoot.")
            print("="*50)
        else:
            print("\nA instancia ja pode estar conectada ou o QR Code nao esta disponivel no momento.")
            print("Verifique o status da instancia no seu painel da Evolution.")

    except Exception as e:
        print(f"Falha no teste: {str(e)}")

if __name__ == "__main__":
    # Ajustar PYTHONPATH para permitir importar 'app'
    # Isso é necessário porque estamos rodando de dentro de backend/tests
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    asyncio.run(run_smoke_test())
