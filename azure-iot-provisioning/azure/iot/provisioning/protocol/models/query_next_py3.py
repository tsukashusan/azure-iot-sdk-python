# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from .query_py3 import Query


class QueryNext(Query):
    """A Json query next request.

    All required parameters must be populated in order to send to Azure.

    :param query_type: Required. Constant filled by server.
    :type query_type: str
    :param continuation_token: The continuation token to get the next page
     results.
    :type continuation_token: str
    """

    _validation = {"query_type": {"required": True}}

    _attribute_map = {
        "query_type": {"key": "queryType", "type": "str"},
        "continuation_token": {"key": "continuationToken", "type": "str"},
    }

    def __init__(self, *, continuation_token: str = None, **kwargs) -> None:
        super(QueryNext, self).__init__(**kwargs)
        self.continuation_token = continuation_token
        self.query_type = "QueryNext"