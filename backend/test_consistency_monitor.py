#!/usr/bin/env python3
"""
Teste rápido do ConsistencyMonitor.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from app.services.consistency_monitor import ConsistencyMonitor

async def test_monitor():
    """Testa o monitor de consistência."""
    print("🔍 Testando ConsistencyMonitor...")
    
    try:
        monitor = ConsistencyMonitor()
        
        # Testar status
        print("\n📊 Obtendo status do monitor...")
        status = await monitor.get_monitoring_status()
        
        print(f"✅ Status geral: {status['overall_status']}")
        print(f"✅ Taxa de consistência: {status['consistency_rate']:.2%}")
        print(f"✅ Total verificado: {status['total_checked']}")
        print(f"✅ Inconsistências: {status['inconsistencies_found']}")
        
        if status['inconsistencies_found'] > 0:
            print(f"\n⚠️ Detalhes das inconsistências:")
            breakdown = status['breakdown']
            print(f"   - Faltando em services: {breakdown['missing_in_services']}")
            print(f"   - Faltando em subscriptions: {breakdown['missing_in_subscriptions']}")
            print(f"   - Conflitos de status: {breakdown['status_mismatches']}")
            print(f"   - Conflitos de data: {breakdown['date_conflicts']}")
        
        print(f"\n🔧 Configuração do monitor:")
        config = status['monitoring_config']
        print(f"   - Intervalo de verificação: {config['check_interval_minutes']} min")
        print(f"   - Cooldown de alertas: {config['alert_cooldown_minutes']} min")
        
        print(f"\n🚨 Thresholds de alerta:")
        thresholds = status['thresholds']
        for key, value in thresholds.items():
            print(f"   - {key}: {value}")
        
        print("\n✅ Teste do ConsistencyMonitor concluído com sucesso!")
        
    except Exception as e:
        print(f"💥 Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_monitor())