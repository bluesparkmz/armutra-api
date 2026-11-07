from decimal import Decimal

# Preço inicial de TESTE: todos os planos custam 1 MT. Para preços reais, altere só aqui.
TEST_PRICE = Decimal("1.00")
CURRENCY = "MZN"

PLANS: dict[str, dict] = {
    "basico": {
        "nome": "Básico",
        "dias": 3,
        "preco": TEST_PRICE,
        "descricao": "Destaque no topo das listas durante 3 dias",
    },
    "plus": {
        "nome": "Plus",
        "dias": 7,
        "preco": TEST_PRICE,
        "descricao": "Destaque no topo das listas durante 7 dias",
    },
    "pro": {
        "nome": "Pro",
        "dias": 15,
        "preco": TEST_PRICE,
        "descricao": "Destaque no topo das listas durante 15 dias",
    },
}
