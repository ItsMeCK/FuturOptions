import pandas as pd

class MoatAgent:
    def __init__(self):
        # Filter Thresholds (from Strategy)
        self.min_roe = 0.15 # 15%
        self.max_debt_equity = 0.5
        self.min_market_cap = 1000 * 10000000 # 1000 Cr (Small cap floor)

    def filter_stocks(self, df):
        """
        Applies Moat filters to the dataframe.
        """
        if df.empty:
            return df

        # 1. ROE Filter
        passed_roe = df[df['ROE'] > self.min_roe]
        
        # 2. Debt Filter
        passed_debt = passed_roe[passed_roe['DebtToEquity'] < self.max_debt_equity]
        
        # 3. Cash Flow Check (CFO > 0)
        passed_cf = passed_debt[passed_debt['OperatingCashFlow'] > 0]
        
        # 4. Growth Check (Positive Revenue Growth)
        final_list = passed_cf[passed_cf['RevenueGrowth'] > 0]
        
        return final_list.sort_values(by='ROE', ascending=False)

    def analyze_valuation(self, df):
        """
        Adds valuation flags (Cheap/Expensive).
        """
        # Simple relative valuation (lower half of PE in the list)
        median_pe = df['TrailingPE'].median()
        df['Valuation'] = df['TrailingPE'].apply(lambda x: 'Undervalued' if x < median_pe else 'Fair/Overvalued')
        return df
