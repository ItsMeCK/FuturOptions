import numpy as np
from scipy.stats import norm
from py_vollib.black_scholes import black_scholes
from py_vollib.black_scholes.greeks.analytical import delta, gamma, theta, vega, rho
from py_vollib.black_scholes.implied_volatility import implied_volatility

class GreeksCalculator:
    """
    Calculates Option Greeks and Implied Volatility using Black-Scholes model.
    """

    @staticmethod
    def calculate_iv(price, S, K, t, r, flag):
        """
        Calculate Implied Volatility.
        
        :param price: Option Market Price
        :param S: Underlying Price
        :param K: Strike Price
        :param t: Time to Expiration (in years)
        :param r: Risk-free Interest Rate
        :param flag: 'c' for Call, 'p' for Put
        :return: Implied Volatility (sigma)
        """
        try:
            return implied_volatility(price, S, K, t, r, flag)
        except Exception as e:
            # print(f"Error calculating IV: {e}")
            return 0.0

    @staticmethod
    def calculate_greeks(S, K, t, r, sigma, flag):
        """
        Calculate Delta, Gamma, Theta, Vega, Rho.
        
        :param S: Underlying Price
        :param K: Strike Price
        :param t: Time to Expiration (in years)
        :param r: Risk-free Interest Rate
        :param sigma: Implied Volatility
        :param flag: 'c' for Call, 'p' for Put
        :return: Dictionary of Greeks
        """
        try:
            d = delta(flag, S, K, t, r, sigma)
            g = gamma(flag, S, K, t, r, sigma)
            th = theta(flag, S, K, t, r, sigma)
            v = vega(flag, S, K, t, r, sigma)
            rh = rho(flag, S, K, t, r, sigma)
            
            return {
                "delta": d,
                "gamma": g,
                "theta": th,
                "vega": v,
                "rho": rh
            }
        except Exception as e:
            # print(f"Error calculating Greeks: {e}")
            return {
                "delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0
            }

    @staticmethod
    def get_days_to_expiry(expiry_date):
        """
        Calculate days to expiry from a date string.
        """
        from datetime import datetime
        today = datetime.now()
        exp = datetime.strptime(expiry_date, "%Y-%m-%d")
        return (exp - today).days / 365.0
