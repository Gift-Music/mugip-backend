from datetime import datetime
from typing import Any

from elasticsearch_dsl import Date, Document, analyzer, tokenizer

from app.constants import TZ_UTC

nori = analyzer(
    'nori',
    tokenizer=tokenizer('nori_token', type='nori_tokenizer', decompound_mode='mixed'),
)


DEFAULT_TEXT_FIELDS = {
    'nori': {
        'type': 'text',
        'analyzer': nori,
        'search_analyzer': 'standard'
    }
}


class DocumnetBase(Document):
    created = Date()
    last_updated = Date()

    class Index:
        name = 'mugip'

    def save(self, **kwargs: dict[str, Any]) -> Any:
        self.created = datetime.now(tz=TZ_UTC)
        self.last_updated = datetime.now(tz=TZ_UTC)
        return super().save(**kwargs)

    def update(self, **kwargs: dict[str, Any]) -> Any:
        self.last_updated = datetime.now(tz=TZ_UTC)
        return super().update(**kwargs)
