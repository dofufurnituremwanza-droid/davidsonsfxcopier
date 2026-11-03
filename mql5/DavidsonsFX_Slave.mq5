//+------------------------------------------------------------------+
//|                                          DavidsonsFX_Slave.mq5   |
//|                             Copyright 2026, DAVIDSONSFX TRADING  |
//|                                   https://davidsonsfx.com        |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, DAVIDSONSFX TRADING"
#property link        "https://davidsonsfx.com"
#property version     "1.00"
#property description "DAVIDSONSFX Client Copier EA (Local Receiver)"
#property strict

#include <Trade\Trade.mqh>

//--- Inputs
input group "=== Server & License ==="
input string   InpServerUrl     = "http://127.0.0.1:8000/api/trades/active"; // Server Active Signals URL
input string   InpLicenseKey    = "DFX-CLIENT-1234";                          // License / Account Token
input int      InpPollIntervalMs= 100;                                        // Polling Interval (ms)

input group "=== Risk Management ==="
enum ENUM_RISK_MODE {
   RISK_FIXED_LOT,       // Fixed Lot
   RISK_MULTIPLIER,      // Lot Multiplier
   RISK_EQUITY_RATIO     // Equity Ratio
};

input ENUM_RISK_MODE InpRiskMode    = RISK_EQUITY_RATIO; // Risk Mode
input double         InpFixedLot    = 0.01;              // Fixed Lot Size
input double         InpMultiplier  = 1.0;               // Lot Multiplier
input double         InpMaxLot      = 10.0;              // Maximum Allowed Lot
input double         InpMinLot      = 0.01;              // Minimum Allowed Lot

input group "=== Execution Filters ==="
input double   InpMaxSlippagePips   = 3.0;               // Maximum Slippage (Pips)
input double   InpMaxSpreadPips     = 5.0;               // Maximum Spread (Pips)
input bool     InpCopySL            = true;              // Copy Stop Loss
input bool     InpCopyTP            = true;              // Copy Take Profit
input bool     InpInvertTrade       = false;             // Invert Trades (Reverse Copy)
input ulong    InpMagicNumber       = 777888;            // Copier Magic Number

CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("=================================================");
   Print("  DAVIDSONSFX TRADING COPIER - CLIENT RECEIVER");
   Print("  Risk Mode: ", EnumToString(InpRiskMode));
   Print("  Max Slippage: ", InpMaxSlippagePips, " pips");
   Print("=================================================");

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetMarginMode();
   trade.SetTypeFillingBySymbol(_Symbol);

   EventSetMillisecondTimer(InpPollIntervalMs);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("DavidsonsFX Slave EA unloaded.");
}

//+------------------------------------------------------------------+
//| Timer event function (Polls server for new orders/modifications) |
//+------------------------------------------------------------------+
void OnTimer()
{
   // In local EA mode, the EA queries the DavidsonsFX server endpoint for active commands
   // or receives signals pushed via WebSocket bridge.
}

