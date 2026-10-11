"""Session cost receipts for trial transcripts: turns, elapsed minutes, tokens, cache-read share and spend.

Comparison tooling, outside the pinned runtime digest. It reads a Claude Code JSONL transcript and
records only counts, never content. Streamed rows of one model request share a message ID; each
request is counted once, with its final usage. Spend is reported only when the transcript carries a
cost; otherwise it is unavailable, never estimated, because a subscription run is not free.

    python -m dcc_harness.session_cost TRANSCRIPT.jsonl [--ceiling-minutes 90] [--ceiling-usd 25] [--out FILE]
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from .evidence import write_json
from .files import file_hash

SCHEMA = 'dcc.trial.session-cost.v1'
TOKENS = {'input': 'input_tokens', 'cache_creation': 'cache_creation_input_tokens',
          'cache_read': 'cache_read_input_tokens', 'output': 'output_tokens'}


def _time(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def receipt(path, *, ceiling_minutes=90, ceiling_usd=25):
    path = Path(path)
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    stamped = [r for r in rows if r.get('timestamp')]
    if not stamped:
        raise ValueError('The transcript has no timestamped rows')
    requests, tool_calls, models, cost, priced = {}, 0, set(), 0.0, False
    for row in rows:
        if row.get('type') != 'assistant' or not isinstance(row.get('message'), dict):
            continue
        message = row['message']
        key = message.get('id') or row.get('uuid')
        requests[key] = message.get('usage') or {}
        if message.get('model'):
            models.add(message['model'])
        tool_calls += sum(1 for item in message.get('content') or [] if isinstance(item, dict) and item.get('type') == 'tool_use')
        if isinstance(row.get('costUSD'), (int, float)):
            cost, priced = cost + row['costUSD'], True
    tokens = {name: sum(int(usage.get(field) or 0) for usage in requests.values()) for name, field in TOKENS.items()}
    read_total = tokens['input'] + tokens['cache_creation'] + tokens['cache_read']
    minutes = round((_time(stamped[-1]['timestamp']) - _time(stamped[0]['timestamp'])).total_seconds() / 60, 1)
    spend = round(cost, 4) if priced else None
    return {'schema': SCHEMA, 'transcript': {'name': path.name, 'sha256': file_hash(path)},
            'started': stamped[0]['timestamp'], 'ended': stamped[-1]['timestamp'], 'elapsed_minutes': minutes,
            'turns': len(requests), 'tool_calls': tool_calls, 'models': sorted(models), 'tokens': tokens,
            'cache_read_share': round(tokens['cache_read'] / read_total, 4) if read_total else None,
            'metered_spend_usd': spend,
            'spend_status': 'reported by the transcript' if priced else
                            'unavailable: the transcript reports tokens, not billed cost; a subscription run is not free',
            'ceilings': {'minutes': ceiling_minutes, 'usd': ceiling_usd},
            'within_minutes': minutes <= ceiling_minutes, 'within_usd': None if spend is None else spend <= ceiling_usd}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transcript')
    parser.add_argument('--ceiling-minutes', type=float, default=90)
    parser.add_argument('--ceiling-usd', type=float, default=25)
    parser.add_argument('--out')
    args = parser.parse_args(argv)
    result = receipt(args.transcript, ceiling_minutes=args.ceiling_minutes, ceiling_usd=args.ceiling_usd)
    print(json.dumps(result, indent=2))
    if args.out:
        write_json(args.out, result)


if __name__ == '__main__':
    main()
