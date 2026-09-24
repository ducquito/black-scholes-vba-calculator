Function NormSDist(x As Double) As Double
    NormSDist = Application.WorksheetFunction.Norm_S_Dist(x, True)
End Function

Function NormSDensity(x As Double) As Double
    NormSDensity = Application.WorksheetFunction.Norm_S_Dist(x, False)
End Function

Function CallPrice(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    Dim d2 As Double
    
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    d2 = d1 - sigma * Sqr(T)
    
    CallPrice = S * NormSDist(d1) - K * Exp(-r * T) * NormSDist(d2)
End Function

Function PutPrice(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    Dim d2 As Double
    
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    d2 = d1 - sigma * Sqr(T)
    
    PutPrice = K * Exp(-r * T) * NormSDist(-d2) - S * NormSDist(-d1)
End Function

Function CallDelta(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    CallDelta = NormSDist(d1)
End Function

Function PutDelta(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    PutDelta = NormSDist(d1) - 1
End Function

Function OptGamma(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    OptGamma = NormSDensity(d1) / (S * sigma * Sqr(T))
End Function

Function Vega(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    Vega = S * NormSDensity(d1) * Sqr(T)
End Function

Function CallTheta(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    Dim d2 As Double
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    d2 = d1 - sigma * Sqr(T)
    CallTheta = -(S * NormSDensity(d1) * sigma) / (2 * Sqr(T)) - r * K * Exp(-r * T) * NormSDist(d2)
End Function

Function PutTheta(S As Double, K As Double, T As Double, r As Double, sigma As Double) As Double
    Dim d1 As Double
    Dim d2 As Double
    d1 = (Log(S / K) + (r + sigma ^ 2 / 2) * T) / (sigma * Sqr(T))
    d2 = d1 - sigma * Sqr(T)
    PutTheta = -(S * NormSDensity(d1) * sigma) / (2 * Sqr(T)) + r * K * Exp(-r * T) * NormSDist(-d2)
End Function
