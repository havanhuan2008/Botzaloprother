from .extensions import db
from .models import AutoReplyRule, MessageLog
from .zalo import ZaloClient


def find_matching_rule(incoming_text: str):
    rules = AutoReplyRule.query.filter_by(is_active=True).order_by(AutoReplyRule.priority.asc(), AutoReplyRule.id.asc()).all()

    fallback_rule = None
    for rule in rules:
        if rule.match_type == 'fallback':
            fallback_rule = rule
            continue
        if rule.matches(incoming_text or ''):
            return rule
    return fallback_rule


def process_incoming_message(user_id: str | None, incoming_text: str | None, raw_payload: str | None):
    log = MessageLog(
        user_id=user_id,
        incoming_text=incoming_text,
        raw_payload=raw_payload,
        status='received',
    )
    db.session.add(log)
    db.session.commit()

    if not user_id or not incoming_text:
        log.status = 'ignored'
        db.session.commit()
        return {'ok': True, 'message': 'No actionable text found'}

    rule = find_matching_rule(incoming_text)
    if not rule:
        log.status = 'no_rule'
        db.session.commit()
        return {'ok': True, 'message': 'No matching rule'}

    reply_text = rule.reply_text.strip()
    result = ZaloClient().send_text_message(user_id, reply_text)

    log.matched_rule_name = rule.name
    log.reply_text = reply_text
    log.status = 'replied' if result.get('ok') else 'send_failed'
    db.session.commit()

    return result
