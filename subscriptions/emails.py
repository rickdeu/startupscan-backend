import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

ADMIN_EMAIL = 'hangaloandre@gmail.com'
SITE_URL = getattr(settings, 'SITE_URL', 'https://startupscan.io')


def _send(subject: str, html_body: str, to: list[str]):
    try:
        text_body = strip_tags(html_body)
        bcc = [ADMIN_EMAIL] if ADMIN_EMAIL not in to else []
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            bcc=bcc,
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
    except Exception as exc:
        logger.error('Falha ao enviar email "%s" para %s: %s', subject, to, exc)


def _base(title: str, body_html: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#0a1120;color:#e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);padding:24px 32px;">
        <h1 style="margin:0;font-size:1.4rem;color:#fff;">StartupScan</h1>
        <p style="margin:4px 0 0;font-size:.85rem;color:rgba(255,255,255,.7);">Plataforma de análise de startups</p>
      </div>
      <div style="padding:32px;">
        <h2 style="color:#f1f5f9;margin-top:0;">{title}</h2>
        {body_html}
      </div>
      <div style="padding:16px 32px;background:#060d1a;text-align:center;font-size:.75rem;color:#475569;">
        StartupScan &mdash; <a href="{SITE_URL}" style="color:#60a5fa;">startupscan.io</a>
      </div>
    </div>
    """


def _now_str() -> str:
    return datetime.utcnow().strftime('%d/%m/%Y às %H:%M UTC')


# ─── Account ─────────────────────────────────────────────────────────────────

def send_account_created(user, trial_end):
    body = f"""
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>A sua conta foi criada com sucesso no <strong>StartupScan</strong>.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:.88rem;">
      <tr><td style="padding:6px 0;color:#64748b;">Utilizador</td><td style="color:#e2e8f0;">{user.username}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Email</td><td style="color:#e2e8f0;">{user.email}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Plano</td><td style="color:#34d399;">Trial (7 dias grátis)</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Trial expira</td><td style="color:#e2e8f0;">{trial_end.strftime('%d/%m/%Y às %H:%M UTC') if trial_end else '—'}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Registado em</td><td style="color:#e2e8f0;">{_now_str()}</td></tr>
    </table>
    <p>Durante o trial pode realizar até <strong>3 análises</strong> com o modelo local.</p>
    <p><a href="{SITE_URL}/subscription/plans/" style="color:#60a5fa;">Ver planos disponíveis &rarr;</a></p>
    """
    _send('Bem-vindo ao StartupScan – Conta criada', _base('Bem-vindo!', body), [user.email])


# ─── Trial ───────────────────────────────────────────────────────────────────

def send_trial_started(user, trial_end):
    body = f"""
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>O seu período de trial de <strong>7 dias</strong> foi ativado com sucesso.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:.88rem;">
      <tr><td style="padding:6px 0;color:#64748b;">Email</td><td style="color:#e2e8f0;">{user.email}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Trial expira</td><td style="color:#e2e8f0;">{trial_end.strftime('%d/%m/%Y às %H:%M UTC') if trial_end else '—'}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Análises incluídas</td><td style="color:#e2e8f0;">3 por mês</td></tr>
    </table>
    <p>Para aceder a todas as funcionalidades, faça upgrade para um plano pago.</p>
    <p><a href="{SITE_URL}/subscription/plans/" style="color:#60a5fa;">Ver planos &rarr;</a></p>
    """
    _send('Bem-vindo ao StartupScan – Trial ativado', _base('Trial ativado!', body), [user.email])


# ─── Subscription activated ──────────────────────────────────────────────────

def send_subscription_activated(user, plan):
    interval_label = {'month': 'mensal', 'year': 'anual', 'once': 'único'}.get(
        getattr(plan, 'interval', ''), getattr(plan, 'interval', '')
    )
    body = f"""
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>A sua subscrição foi ativada com sucesso!</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:.88rem;">
      <tr><td style="padding:6px 0;color:#64748b;">Utilizador</td><td style="color:#e2e8f0;">{user.username}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Email</td><td style="color:#e2e8f0;">{user.email}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Plano</td><td style="color:#34d399;"><strong>{plan.name}</strong></td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Tier</td><td style="color:#e2e8f0;">{plan.tier.upper()}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Faturação</td><td style="color:#e2e8f0;">{interval_label.capitalize()}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Preço</td><td style="color:#e2e8f0;">${plan.price_usd} USD</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Ativada em</td><td style="color:#e2e8f0;">{_now_str()}</td></tr>
    </table>
    <p>Já tem acesso a todas as funcionalidades do plano <strong>{plan.tier.upper()}</strong>.</p>
    <p><a href="{SITE_URL}/subscription/plans/" style="color:#60a5fa;">Gerir subscrição &rarr;</a></p>
    """
    _send(
        f'Subscrição {plan.name} ativada – StartupScan',
        _base('Subscrição ativada!', body),
        [user.email],
    )


# ─── Subscription updated (plan change) ──────────────────────────────────────

def send_subscription_updated(user, old_plan_name: str, new_plan):
    interval_label = {'month': 'mensal', 'year': 'anual', 'once': 'único'}.get(
        getattr(new_plan, 'interval', ''), getattr(new_plan, 'interval', '')
    )
    body = f"""
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>A sua subscrição foi atualizada.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:.88rem;">
      <tr><td style="padding:6px 0;color:#64748b;">Utilizador</td><td style="color:#e2e8f0;">{user.username}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Email</td><td style="color:#e2e8f0;">{user.email}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Plano anterior</td><td style="color:#f59e0b;">{old_plan_name}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Novo plano</td><td style="color:#34d399;"><strong>{new_plan.name}</strong></td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Faturação</td><td style="color:#e2e8f0;">{interval_label.capitalize()}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Novo preço</td><td style="color:#e2e8f0;">${new_plan.price_usd} USD</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Atualizado em</td><td style="color:#e2e8f0;">{_now_str()}</td></tr>
    </table>
    <p><a href="{SITE_URL}/subscription/plans/" style="color:#60a5fa;">Gerir subscrição &rarr;</a></p>
    """
    _send(
        f'Subscrição atualizada: {old_plan_name} → {new_plan.name} – StartupScan',
        _base('Subscrição atualizada', body),
        [user.email],
    )


# ─── Subscription canceled ───────────────────────────────────────────────────

def send_subscription_canceled(user, plan_name: str):
    body = f"""
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>A sua subscrição foi cancelada.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:.88rem;">
      <tr><td style="padding:6px 0;color:#64748b;">Utilizador</td><td style="color:#e2e8f0;">{user.username}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Email</td><td style="color:#e2e8f0;">{user.email}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Plano cancelado</td><td style="color:#f87171;">{plan_name}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Cancelado em</td><td style="color:#e2e8f0;">{_now_str()}</td></tr>
    </table>
    <p>Continuará a ter acesso até ao fim do período atual.</p>
    <p><a href="{SITE_URL}/subscription/plans/" style="color:#60a5fa;">Reativar subscrição &rarr;</a></p>
    """
    _send(
        'Subscrição cancelada – StartupScan',
        _base('Subscrição cancelada', body),
        [user.email],
    )


# ─── Payment failed ──────────────────────────────────────────────────────────

def send_payment_failed(user, plan_name: str):
    body = f"""
    <p>Olá <strong>{user.first_name or user.username}</strong>,</p>
    <p>Não foi possível processar o pagamento da sua subscrição.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:.88rem;">
      <tr><td style="padding:6px 0;color:#64748b;">Utilizador</td><td style="color:#e2e8f0;">{user.username}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Email</td><td style="color:#e2e8f0;">{user.email}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Plano</td><td style="color:#f87171;">{plan_name}</td></tr>
      <tr><td style="padding:6px 0;color:#64748b;">Falha em</td><td style="color:#e2e8f0;">{_now_str()}</td></tr>
    </table>
    <p>Por favor, atualize os seus dados de pagamento para manter o acesso.</p>
    <p><a href="{SITE_URL}/subscription/billing-portal/" style="color:#60a5fa;">Atualizar método de pagamento &rarr;</a></p>
    """
    _send(
        'Ação necessária: falha no pagamento – StartupScan',
        _base('Falha no pagamento', body),
        [user.email],
    )
