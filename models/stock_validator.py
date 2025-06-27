class StockValidator:
    """Basic stock data validator"""
    
    def __init__(self):
        pass
        
    def validate(self, stock_data: dict) -> bool:
        """Validate stock data structure"""
        required_fields = {'symbol', 'price', 'volume'}
        return all(field in stock_data for field in required_fields)
