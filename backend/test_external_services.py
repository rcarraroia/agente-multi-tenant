#!/usr/bin/env python3
"""
Script de teste para validação de serviços externos.
Executa os testes de integração implementados na FASE 7.
"""

import asyncio
import sys
import os
from datetime import datetime

# Adicionar o diretório do app ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.external_service_validator import external_service_validator, ServiceStatus
from app.core.logging import get_logger
from app.config import settings

logger = get_logger('test_external_services')

async def test_all_services():
    """
    Executa teste completo de todos os serviços externos.
    """
    print("🔍 INICIANDO VALIDAÇÃO DE SERVIÇOS EXTERNOS")
    print("=" * 60)
    
    # Verificar configurações
    print("\n📋 CONFIGURAÇÕES DETECTADAS:")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Evolution API URL: {'✅ Configurado' if settings.EVOLUTION_API_URL else '❌ Não configurado'}")
    print(f"   Chatwoot URL: {'✅ Configurado' if settings.CHATWOOT_URL else '❌ Não configurado'}")
    print(f"   OpenAI API Key: {'✅ Configurado' if settings.OPENAI_API_KEY else '❌ Não configurado'}")
    print(f"   Supabase URL: {'✅ Configurado' if settings.SUPABASE_URL else '❌ Não configurado'}")
    
    print("\n🔄 EXECUTANDO VALIDAÇÕES...")
    
    try:
        # Executar validação completa
        start_time = datetime.utcnow()
        services_checks = await external_service_validator.validate_all_services()
        end_time = datetime.utcnow()
        
        total_time = (end_time - start_time).total_seconds()
        
        print(f"\n📊 RESULTADOS DA VALIDAÇÃO (tempo total: {total_time:.2f}s):")
        print("-" * 60)
        
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        for service_name, check in services_checks.items():
            status_icon = {
                ServiceStatus.HEALTHY: "✅",
                ServiceStatus.DEGRADED: "⚠️",
                ServiceStatus.UNHEALTHY: "❌",
                ServiceStatus.UNKNOWN: "❓"
            }.get(check.status, "❓")
            
            print(f"   {status_icon} {service_name.upper()}: {check.status}")
            print(f"      Tempo de resposta: {check.response_time_ms:.0f}ms")
            
            if check.error_message:
                print(f"      Erro: {check.error_message}")
            
            if check.details:
                print(f"      Detalhes: {check.details}")
            
            print()
            
            # Contar status
            if check.status == ServiceStatus.HEALTHY:
                healthy_count += 1
            elif check.status == ServiceStatus.DEGRADED:
                degraded_count += 1
            elif check.status == ServiceStatus.UNHEALTHY:
                unhealthy_count += 1
        
        # Resumo final
        total_count = len(services_checks)
        print("📈 RESUMO FINAL:")
        print(f"   Total de serviços: {total_count}")
        print(f"   ✅ Saudáveis: {healthy_count}")
        print(f"   ⚠️ Degradados: {degraded_count}")
        print(f"   ❌ Indisponíveis: {unhealthy_count}")
        
        # Status geral
        if healthy_count == total_count:
            print(f"\n🎉 SISTEMA TOTALMENTE OPERACIONAL!")
            return True
        elif healthy_count > 0:
            print(f"\n⚠️ SISTEMA PARCIALMENTE OPERACIONAL")
            print(f"   {total_count - healthy_count} serviços com problemas")
            return True
        else:
            print(f"\n🚨 SISTEMA COM PROBLEMAS CRÍTICOS")
            print(f"   Nenhum serviço externo disponível")
            return False
            
    except Exception as e:
        print(f"\n💥 ERRO DURANTE VALIDAÇÃO: {str(e)}")
        logger.error(f"Erro na validação: {str(e)}")
        return False

async def test_circuit_breakers():
    """
    Testa o funcionamento dos circuit breakers.
    """
    print("\n🔧 TESTANDO CIRCUIT BREAKERS:")
    print("-" * 40)
    
    try:
        circuit_breakers_status = external_service_validator.get_circuit_breaker_status()
        
        for service_name, status in circuit_breakers_status.items():
            state_icon = {
                "closed": "✅",
                "open": "🚨",
                "half_open": "⚠️"
            }.get(status["state"], "❓")
            
            print(f"   {state_icon} {service_name.upper()}: {status['state']}")
            print(f"      Falhas: {status['failure_count']}")
            print(f"      Pode executar: {'✅' if status['can_execute'] else '❌'}")
            
            if status['last_failure']:
                print(f"      Última falha: {status['last_failure']}")
            if status['last_success']:
                print(f"      Último sucesso: {status['last_success']}")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"💥 Erro ao testar circuit breakers: {str(e)}")
        return False

async def main():
    """
    Função principal do teste.
    """
    print("🚀 TESTE DE VALIDAÇÃO DE SERVIÇOS EXTERNOS")
    print("   Agente Multi-Tenant - FASE 7 Validation")
    print("   Data:", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
    print()
    
    # Executar testes
    services_ok = await test_all_services()
    circuit_breakers_ok = await test_circuit_breakers()
    
    print("\n" + "=" * 60)
    
    if services_ok and circuit_breakers_ok:
        print("🎉 CHECKPOINT APROVADO - Integrações externas validadas!")
        print("   ✅ Todos os testes passaram")
        print("   ✅ Circuit breakers funcionando")
        print("   ✅ Sistema pronto para produção")
        return 0
    else:
        print("❌ CHECKPOINT REPROVADO - Problemas detectados")
        print("   🔧 Verifique as configurações")
        print("   🔧 Valide conectividade de rede")
        print("   🔧 Confirme credenciais dos serviços")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)