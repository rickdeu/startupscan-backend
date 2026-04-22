import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

ADMIN_BCC = 'hangaloandre@gmail.com'


def _send(subject: str, html_body: str, to: list[str]):
    try:
        text_body = strip_tags(html_body)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            bcc=[ADMIN_BCC] if ADMIN_BCC not in to else [],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
    except Exception as exc:
        logger.error('Falha ao enviar email "%s" para %s: %s', subject, to, exc)


def send_trial_started(user, trial_end):
    html = f"""
    <h2>Bem-vindo ao StartupScan!</h2>
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>O seu período de trial de <strong>7 dias</strong> foi ativado com sucesso.</p>
    <p>O trial expira em: <strong>{trial_end.strftime('%d/%m/%Y às %H:%M UTC')}</strong></p>
    <p>Durante o trial pode realizar até 3 análises de pitch com o modelo local.
    Para aceder a todas as funcionalidades, faça upgrade para um plano pago.</p>
    <p><a href="{getattr(settings, 'SITE_URL', '')}/subscription/plans/">Ver planos disponíveis</a></p>
    <hr><p style="font-size:12px;color:#888;">StartupScan — Plataforma de análise de startups</p>
    """
    _send('Bem-vindo ao StartupScan – Trial ativado', html, [user.email])


def send_subscription_activated(user, plan):
    html = f"""
    <h2>Subscrição ativada!</h2>
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>A sua subscrição <strong>{plan.name}</strong> foi ativada com sucesso.</p>
    <p>Já tem acesso a todas as funcionalidades do plano {plan.tier.upper()}.</p>
    <p><a href="{getattr(settings, 'SITE_URL', '')}/subscription/plans/">Gerir subscrição</a></p>
    <hr><p style="font-size:12px;color:#888;">StartupScan</p>
    """
    _send(f'Subscrição {plan.name} ativada – StartupScan', html, [user.email])


def send_subscription_canceled(user, plan_name: str):
    html = f"""
    <h2>Subscrição cancelada</h2>
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>A sua subscrição <strong>{plan_name}</strong> foi cancelada.</p>
    <p>Continuará a ter acesso até ao fim do período atual.</p>
    <p><a href="{getattr(settings, 'SITE_URL', '')}/subscription/plans/">Reativar subscrição</a></p>
    <hr><p style="font-size:12px;color:#888;">StartupScan</p>
    """
    _send('Subscrição cancelada – StartupScan', html, [user.email])


def send_payment_failed(user, plan_name: str):
    html = f"""
    <h2>Falha no pagamento</h2>
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>Não foi possível processar o pagamento da sua subscrição <strong>{plan_name}</strong>.</p>
    <p>Por favor, atualize os seus dados de pagamento para manter o acesso.</p>
    <p><a href="{getattr(settings, 'SITE_URL', '')}/subscription/billing-portal/">Atualizar método de pagamento</a></p>
    <hr><p style="font-size:12px;color:#888;">StartupScan</p>
    """
    _send('Ação necessária: falha no pagamento – StartupScan', html, [user.email])
