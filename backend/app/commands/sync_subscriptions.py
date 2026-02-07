"""
Comando CLI para sincronização de assinaturas.

Script para executar sincronização manual entre affiliate_services
e multi_agent_subscriptions, com opções de configuração.
"""

import asyncio
import sys
import argparse
from datetime import datetime
from typing import Optional
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.subscription_synchronizer import SubscriptionSynchronizer
from app.schemas.subscription_sync import SubscriptionSyncConfig, SubscriptionSource
from app.core.logging import setup_logging, get_logger

# Configurar logging
setup_logging()
logger = get_logger('sync_command')

async def sync_all_subscriptions(config: SubscriptionSyncConfig):
    """Executa sincronização completa de assinaturas."""
    logger.info("🚀 Iniciando comando de sincronização de assinaturas")
    logger.info(f"   Configuração: {config.model_dump()}")
    
    try:
        synchronizer = SubscriptionSynchronizer()
        result = await synchronizer.synchronize_all(config)
        
        # Exibir resultados
        print("\n" + "="*60)
        print("📊 RESULTADO DA SINCRONIZAÇÃO")
        print("="*60)
        print(f"Total processado:     {result.total_processed}")
        print(f"Sucessos:            {result.successful_syncs}")
        print(f"Conflitos:           {result.conflicts_found}")
        print(f"Erros:               {result.errors_encountered}")
        print(f"Tempo execução:      {result.execution_time_seconds:.2f}s")
        
        if result.conflict_summary:
            print(f"\n📋 RESUMO DE CONFLITOS:")
            for conflict_type, count in result.conflict_summary.items():
                print(f"  - {conflict_type}: {count}")
        
        if result.error_affiliates:
            print(f"\n❌ AFILIADOS COM ERRO:")
            for affiliate_id in result.error_affiliates[:5]:  # Mostrar apenas os primeiros 5
                print(f"  - {affiliate_id}")
            if len(result.error_affiliates) > 5:
                print(f"  ... e mais {len(result.error_affiliates) - 5}")
        
        print("="*60)
        
        # Status de saída
        if result.errors_encountered > 0:
            logger.error("❌ Sincronização concluída com erros")
            return 1
        elif result.conflicts_found > 0:
            logger.warning("⚠️ Sincronização concluída com conflitos")
            return 0
        else:
            logger.info("✅ Sincronização concluída com sucesso")
            return 0
            
    except Exception as e:
        logger.error(f"💥 Erro na sincronização: {str(e)}")
        print(f"\n❌ ERRO: {str(e)}")
        return 1

async def validate_consistency():
    """Executa validação de consistência."""
    logger.info("🔍 Iniciando validação de consistência")
    
    try:
        synchronizer = SubscriptionSynchronizer()
        result = await synchronizer.validate_consistency()
        
        # Exibir resultados
        print("\n" + "="*60)
        print("🔍 RESULTADO DA VALIDAÇÃO")
        print("="*60)
        print(f"Consistente:         {'✅ SIM' if result.is_consistent else '❌ NÃO'}")
        print(f"Total verificado:    {result.total_checked}")
        print(f"Inconsistências:     {result.inconsistencies_found}")
        
        if not result.is_consistent:
            print(f"\n📋 DETALHES DAS INCONSISTÊNCIAS:")
            print(f"  Faltando em services:      {len(result.missing_in_services)}")
            print(f"  Faltando em subscriptions: {len(result.missing_in_subscriptions)}")
            print(f"  Conflitos de status:       {len(result.status_mismatches)}")
            print(f"  Conflitos de data:         {len(result.date_conflicts)}")
        
        if result.validation_errors:
            print(f"\n❌ ERROS ENCONTRADOS:")
            for error in result.validation_errors[:10]:  # Mostrar apenas os primeiros 10
                print(f"  - {error}")
            if len(result.validation_errors) > 10:
                print(f"  ... e mais {len(result.validation_errors) - 10}")
        
        if result.validation_warnings:
            print(f"\n⚠️ AVISOS:")
            for warning in result.validation_warnings[:5]:
                print(f"  - {warning}")
            if len(result.validation_warnings) > 5:
                print(f"  ... e mais {len(result.validation_warnings) - 5}")
        
        print("="*60)
        
        return 0 if result.is_consistent else 1
        
    except Exception as e:
        logger.error(f"💥 Erro na validação: {str(e)}")
        print(f"\n❌ ERRO: {str(e)}")
        return 1

async def show_unified_subscription(affiliate_id: str):
    """Mostra a visão unificada de uma assinatura específica."""
    logger.info(f"🔍 Obtendo assinatura unificada para afiliado {affiliate_id}")
    
    try:
        from uuid import UUID
        affiliate_uuid = UUID(affiliate_id)
        
        synchronizer = SubscriptionSynchronizer()
        unified = await synchronizer.get_unified_subscription(affiliate_uuid)
        
        if not unified:
            print(f"\n❌ Nenhuma assinatura encontrada para afiliado {affiliate_id}")
            return 1
        
        # Exibir dados unificados
        print("\n" + "="*60)
        print(f"📊 ASSINATURA UNIFICADA - {affiliate_id}")
        print("="*60)
        print(f"Status:              {unified.status.value}")
        print(f"Ativo:               {'✅ SIM' if unified.is_active else '❌ NÃO'}")
        print(f"Tenant ID:           {unified.tenant_id or 'N/A'}")
        print(f"Fonte primária:      {unified.primary_source.value}")
        print(f"Última sincronização: {unified.last_synced_at.strftime('%d/%m/%Y %H:%M:%S')}")
        
        print(f"\n📋 DADOS DE SERVIÇO:")
        print(f"  Tipo:              {unified.service_type or 'N/A'}")
        print(f"  Expira em:         {unified.service_expires_at.strftime('%d/%m/%Y') if unified.service_expires_at else 'N/A'}")
        
        print(f"\n💳 DADOS DE ASSINATURA:")
        print(f"  Asaas ID:          {unified.asaas_subscription_id or 'N/A'}")
        print(f"  Cliente ID:        {unified.asaas_customer_id or 'N/A'}")
        print(f"  Valor mensal:      R$ {(unified.plan_value_cents / 100):.2f}" if unified.plan_value_cents else "  Valor mensal:      N/A")
        print(f"  Tipo cobrança:     {unified.billing_type or 'N/A'}")
        print(f"  Próximo vencimento: {unified.next_due_date.strftime('%d/%m/%Y') if unified.next_due_date else 'N/A'}")
        
        if unified.conflicts:
            print(f"\n⚠️ CONFLITOS IDENTIFICADOS ({len(unified.conflicts)}):")
            for conflict in unified.conflicts:
                print(f"  - {conflict.field_name}: {conflict.severity}")
                print(f"    Services: {conflict.affiliate_services_value}")
                print(f"    Subscriptions: {conflict.multi_agent_subscriptions_value}")
                print(f"    Recomendação: {conflict.recommended_resolution}")
        
        print("="*60)
        
        return 0
        
    except ValueError:
        print(f"\n❌ ERRO: '{affiliate_id}' não é um UUID válido")
        return 1
    except Exception as e:
        logger.error(f"💥 Erro ao obter assinatura: {str(e)}")
        print(f"\n❌ ERRO: {str(e)}")
        return 1

def main():
    """Função principal do comando."""
    parser = argparse.ArgumentParser(
        description="Comando para sincronização de assinaturas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Sincronização completa (dry run)
  python sync_subscriptions.py sync --dry-run

  # Sincronização real com resolução automática
  python sync_subscriptions.py sync --resolve-conflicts

  # Validar consistência
  python sync_subscriptions.py validate

  # Ver assinatura específica
  python sync_subscriptions.py show 12345678-1234-1234-1234-123456789012

  # Sincronização preferindo dados de subscriptions
  python sync_subscriptions.py sync --prefer-source subscriptions
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
    
    # Comando sync
    sync_parser = subparsers.add_parser('sync', help='Sincronizar assinaturas')
    sync_parser.add_argument('--dry-run', action='store_true', 
                           help='Executar sem fazer alterações (apenas simular)')
    sync_parser.add_argument('--resolve-conflicts', action='store_true',
                           help='Resolver conflitos automaticamente')
    sync_parser.add_argument('--prefer-source', choices=['services', 'subscriptions'],
                           default='subscriptions',
                           help='Fonte preferida para resolução de conflitos')
    sync_parser.add_argument('--batch-size', type=int, default=100,
                           help='Tamanho do lote para processamento')
    sync_parser.add_argument('--create-tenants', action='store_true',
                           help='Criar tenants faltantes automaticamente')
    
    # Comando validate
    validate_parser = subparsers.add_parser('validate', help='Validar consistência')
    
    # Comando show
    show_parser = subparsers.add_parser('show', help='Mostrar assinatura específica')
    show_parser.add_argument('affiliate_id', help='ID do afiliado (UUID)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Executar comando
    if args.command == 'sync':
        config = SubscriptionSyncConfig(
            dry_run=args.dry_run,
            resolve_conflicts_automatically=args.resolve_conflicts,
            prefer_source=SubscriptionSource.MULTI_AGENT_SUBSCRIPTIONS if args.prefer_source == 'subscriptions' else SubscriptionSource.AFFILIATE_SERVICES,
            batch_size=args.batch_size,
            create_missing_tenants=args.create_tenants
        )
        return asyncio.run(sync_all_subscriptions(config))
    
    elif args.command == 'validate':
        return asyncio.run(validate_consistency())
    
    elif args.command == 'show':
        return asyncio.run(show_unified_subscription(args.affiliate_id))
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)