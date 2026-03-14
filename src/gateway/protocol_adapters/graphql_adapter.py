import graphene
from fastapi import Request


class GraphQLAdapter:
    """GraphQL protocol adapter"""

    def __init__(self):
        self.schema = None
        self._build_schema()

    def _build_schema(self):
        """Build GraphQL schema"""

        class Query(graphene.ObjectType):
            hello = graphene.String(name=graphene.String(default_value="World"))

            def resolve_hello(self, info, name):
                return f"Hello {name}"

        self.schema = graphene.Schema(query=Query)

    async def handle_request(self, request: Request):
        body = await request.json()

        query = body.get("query")
        variables = body.get("variables", {})

        result = await self.schema.execute_async(
            query,
            variable_values=variables
        )

        return {
            "data": result.data,
            "errors": [str(e) for e in result.errors] if result.errors else None
        }