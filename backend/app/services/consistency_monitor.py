"""
Consistency Monitor Service.

Serviço responsável por monitorar a consistência dos dados
entre affiliate_services e multi_agent_subscriptions,
detectando e alertando sobre inconsistências.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

from app.services.subscription_synchronizer import SubscriptionSynchronizer
from app.schemas.subscription_sync import SubscriptionValidationResult, SubscriptionSyncConfig
from app.core.logging import get_logger, get_structured_logger, AuditLogger
from app.db.supabase import get_supabase

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)
audit_logger = AuditLogger()

class ConsistencyAlert:
    """Representa um alerta de inconsistência."""
    
    def __init__(
        self,
        alert_type: str,
        severity: str,
        message: str,
        affected_affiliates: List[UUID] = None,
        metadata: Dict[str, Any] = None
    ):
        self.alert_type = alert_type
        self.severity = severity  # low, medium, high, critical
        self.message = message
        self.affected_affiliates = affected_affiliates or []
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc)

class ConsistencyMonitor:
    """
    Monitor de consistência de dados.
    
    Responsável por:
    - Verificar consistência periodicamente
    - Detectar inconsistências críticas
    - Gerar alertas automáticos
    - Manter histórico de verificações
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        self.synchronizer = SubscriptionSynchronizer()
        
        # Configurações de monitoramento
        self.check_interval_minutes = 30  # Verificar a cada 30 minutos
        self.alert_thresholds = {
            "missing_services": 5,      # Alerta se > 5 afiliados sem serviços
            "missing_subscriptions": 3, # Alerta se > 3 afiliados sem assinaturas
            "status_mismatches": 10,    # Alerta se > 10 conflitos de status
            "date_conflicts": 15        # Alerta se > 15 conflitos de data
        }
        
        # Cache de alertas para evitar spam
        self.alert_cache = {}
        self.alert_cooldown_minutes = 60  # Não repetir alerta por 1 hora

    async def start_monitoring(self):
        """Inicia o monitoramento contínuo de consistência."""
        logger.info("🔍 Iniciando monitoramento contínuo de consistência")
        logger.info(f"   Intervalo: {self.check_interval_minutes} minutos")
        logger.info(f"   Thresholds: {self.alert_thresholds}")
        
        while True:
            try:
                await self.run_consistency_check()
                
                # Aguardar próxima verificação
                await asyncio.sleep(self.check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"💥 Erro no monitoramento de consistência: {str(e)}")
                # Aguardar menos tempo em caso de erro
                await asyncio.sleep(5 * 60)  # 5 minutos

    async def run_consistency_check(self) -> SubscriptionValidationResult:
        """Executa uma verificação de consistência."""
        logger.info("🔍 Executando verificação de consistência")
        
        try:
            # Executar validação
            result = await self.synchronizer.validate_consistency()
            
            # Registrar resultado
            await self._log_consistency_result(result)
            
            # Verificar se precisa gerar alertas
            alerts = await self._analyze_and_generate_alerts(result)
            
            # Processar alertas
            for alert in alerts:
                await self._process_alert(alert)
            
            logger.info(f"✅ Verificação concluída: {len(alerts)} alertas gerados")
            return result
            
        except Exception as e:
            logger.error(f"💥 Erro na verificação de consistência: {str(e)}")
            
            # Gerar alerta crítico
            critical_alert = ConsistencyAlert(
                alert_type="system_error",
                severity="critical",
                message=f"Falha na verificação de consistência: {str(e)}",
                metadata={"error": str(e)}
            )
            await self._process_alert(critical_alert)
            
            raise

    async def _analyze_and_generate_alerts(self, result: SubscriptionValidationResult) -> List[ConsistencyAlert]:
        """Analisa resultado e gera alertas necessários."""
        alerts = []
        
        # Alerta para muitos serviços faltando
        if len(result.missing_in_services) > self.alert_thresholds["missing_services"]:
            alerts.append(ConsistencyAlert(
                alert_type="missing_services",
                severity="high",
                message=f"{len(result.missing_in_services)} afiliados têm assinaturas mas não têm serviços",
                affected_affiliates=result.missing_in_services,
                metadata={
                    "count": len(result.missing_in_services),
                    "threshold": self.alert_thresholds["missing_services"]
                }
            ))
        
        # Alerta para muitas assinaturas faltando
        if len(result.missing_in_subscriptions) > self.alert_thresholds["missing_subscriptions"]:
            alerts.append(ConsistencyAlert(
                alert_type="missing_subscriptions",
                severity="medium",
                message=f"{len(result.missing_in_subscriptions)} afiliados têm serviços mas não têm assinaturas",
                affected_affiliates=result.missing_in_subscriptions,
                metadata={
                    "count": len(result.missing_in_subscriptions),
                    "threshold": self.alert_thresholds["missing_subscriptions"]
                }
            ))
        
        # Alerta para muitos conflitos de status
        if len(result.status_mismatches) > self.alert_thresholds["status_mismatches"]:
            alerts.append(ConsistencyAlert(
                alert_type="status_mismatches",
                severity="medium",
                message=f"{len(result.status_mismatches)} afiliados têm conflitos de status entre tabelas",
                affected_affiliates=result.status_mismatches,
                metadata={
                    "count": len(result.status_mismatches),
                    "threshold": self.alert_thresholds["status_mismatches"]
                }
            ))
        
        # Alerta para muitos conflitos de data
        if len(result.date_conflicts) > self.alert_thresholds["date_conflicts"]:
            alerts.append(ConsistencyAlert(
                alert_type="date_conflicts",
                severity="low",
                message=f"{len(result.date_conflicts)} afiliados têm conflitos de data entre tabelas",
                affected_affiliates=result.date_conflicts,
                metadata={
                    "count": len(result.date_conflicts),
                    "threshold": self.alert_thresholds["date_conflicts"]
                }
            ))
        
        # Alerta crítico se sistema está muito inconsistente
        if result.inconsistencies_found > (result.total_checked * 0.5):  # > 50% inconsistente
            alerts.append(ConsistencyAlert(
                alert_type="system_critical",
                severity="critical",
                message=f"Sistema altamente inconsistente: {result.inconsistencies_found}/{result.total_checked} registros com problemas",
                metadata={
                    "inconsistency_rate": result.inconsistencies_found / result.total_checked,
                    "total_checked": result.total_checked,
                    "inconsistencies_found": result.inconsistencies_found
                }
            ))
        
        return alerts

    async def _process_alert(self, alert: ConsistencyAlert):
        """Processa um alerta (log, notificação, etc.)."""
        
        # Verificar cooldown
        alert_key = f"{alert.alert_type}_{alert.severity}"
        if self._is_alert_in_cooldown(alert_key):
            logger.debug(f"⏰ Alerta {alert_key} em cooldown, ignorando")
            return
        
        # Registrar alerta
        self.alert_cache[alert_key] = alert.created_at
        
        # Log estruturado
        structured_logger.warning(
            "consistency_alert",
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            affected_count=len(alert.affected_affiliates),
            metadata=alert.metadata
        )
        
        # Log de auditoria
        audit_logger.log_system_event(
            event_type="consistency_alert",
            details={
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "affected_affiliates": [str(aid) for aid in alert.affected_affiliates],
                "metadata": alert.metadata
            }
        )
        
        # Log tradicional baseado na severidade
        if alert.severity == "critical":
            logger.critical(f"🚨 ALERTA CRÍTICO: {alert.message}")
        elif alert.severity == "high":
            logger.error(f"🔴 ALERTA ALTO: {alert.message}")
        elif alert.severity == "medium":
            logger.warning(f"🟡 ALERTA MÉDIO: {alert.message}")
        else:
            logger.info(f"🔵 ALERTA BAIXO: {alert.message}")
        
        # Salvar alerta no banco (opcional)
        await self._save_alert_to_database(alert)

    def _is_alert_in_cooldown(self, alert_key: str) -> bool:
        """Verifica se um alerta está em cooldown."""
        if alert_key not in self.alert_cache:
            return False
        
        last_alert = self.alert_cache[alert_key]
        cooldown_until = last_alert + timedelta(minutes=self.alert_cooldown_minutes)
        
        return datetime.now(timezone.utc) < cooldown_until

    async def _save_alert_to_database(self, alert: ConsistencyAlert):
        """Salva alerta no banco de dados para histórico."""
        try:
            alert_data = {
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "affected_affiliates": [str(aid) for aid in alert.affected_affiliates],
                "metadata": alert.metadata,
                "created_at": alert.created_at.isoformat()
            }
            
            # Salvar na tabela de alertas (se existir)
            # Por enquanto, apenas log
            logger.debug(f"💾 Salvaria alerta no banco: {alert_data}")
            
        except Exception as e:
            logger.error(f"💥 Erro ao salvar alerta no banco: {str(e)}")

    async def _log_consistency_result(self, result: SubscriptionValidationResult):
        """Registra resultado da verificação de consistência."""
        
        # Log estruturado
        structured_logger.info(
            "consistency_check_completed",
            is_consistent=result.is_consistent,
            total_checked=result.total_checked,
            inconsistencies_found=result.inconsistencies_found,
            missing_in_services=len(result.missing_in_services),
            missing_in_subscriptions=len(result.missing_in_subscriptions),
            status_mismatches=len(result.status_mismatches),
            date_conflicts=len(result.date_conflicts),
            validation_errors=len(result.validation_errors),
            validation_warnings=len(result.validation_warnings)
        )
        
        # Log tradicional
        if result.is_consistent:
            logger.info("✅ Sistema consistente - nenhuma inconsistência detectada")
        else:
            logger.warning(f"⚠️ Sistema inconsistente: {result.inconsistencies_found} problemas encontrados")
            logger.warning(f"   Faltando em services: {len(result.missing_in_services)}")
            logger.warning(f"   Faltando em subscriptions: {len(result.missing_in_subscriptions)}")
            logger.warning(f"   Conflitos de status: {len(result.status_mismatches)}")
            logger.warning(f"   Conflitos de data: {len(result.date_conflicts)}")

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Obtém status atual do monitoramento."""
        
        # Executar verificação rápida
        result = await self.synchronizer.validate_consistency()
        
        # Calcular métricas
        consistency_rate = 1.0 - (result.inconsistencies_found / max(result.total_checked, 1))
        
        # Determinar status geral
        if result.is_consistent:
            overall_status = "healthy"
        elif consistency_rate > 0.8:
            overall_status = "warning"
        else:
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "consistency_rate": consistency_rate,
            "last_check": result.validated_at.isoformat(),
            "total_checked": result.total_checked,
            "inconsistencies_found": result.inconsistencies_found,
            "breakdown": {
                "missing_in_services": len(result.missing_in_services),
                "missing_in_subscriptions": len(result.missing_in_subscriptions),
                "status_mismatches": len(result.status_mismatches),
                "date_conflicts": len(result.date_conflicts)
            },
            "thresholds": self.alert_thresholds,
            "monitoring_config": {
                "check_interval_minutes": self.check_interval_minutes,
                "alert_cooldown_minutes": self.alert_cooldown_minutes
            }
        }

    async def force_sync_inconsistencies(self, dry_run: bool = True) -> Dict[str, Any]:
        """Força sincronização para resolver inconsistências detectadas."""
        logger.info(f"🔄 Forçando sincronização de inconsistências (dry_run={dry_run})")
        
        try:
            # Configurar sincronização para resolver conflitos
            config = SubscriptionSyncConfig(
                dry_run=dry_run,
                resolve_conflicts_automatically=True,
                create_missing_tenants=True,
                batch_size=50
            )
            
            # Executar sincronização
            sync_result = await self.synchronizer.synchronize_all(config)
            
            # Log resultado
            logger.info(f"✅ Sincronização concluída:")
            logger.info(f"   Processados: {sync_result.total_processed}")
            logger.info(f"   Sucessos: {sync_result.successful_syncs}")
            logger.info(f"   Conflitos: {sync_result.conflicts_found}")
            logger.info(f"   Erros: {sync_result.errors_encountered}")
            
            return {
                "success": True,
                "dry_run": dry_run,
                "total_processed": sync_result.total_processed,
                "successful_syncs": sync_result.successful_syncs,
                "conflicts_found": sync_result.conflicts_found,
                "errors_encountered": sync_result.errors_encountered,
                "execution_time_seconds": sync_result.execution_time_seconds
            }
            
        except Exception as e:
            logger.error(f"💥 Erro na sincronização forçada: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }