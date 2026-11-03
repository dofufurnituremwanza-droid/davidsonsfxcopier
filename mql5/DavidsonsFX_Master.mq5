//+------------------------------------------------------------------+
//|                                         DavidsonsFX_Master.mq5   |
//|                             Copyright 2026, DAVIDSONSFX TRADING  |
//|                                   https://davidsonsfx.com        |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, DAVIDSONSFX TRADING"
#property link        "https://davidsonsfx.com"
#property version     "1.00"
#property description "DAVIDSONSFX High-Speed Master Trade Transmitter"
#property strict

//--- Inputs
input group "=== Server Configuration ==="
input string   InpServerUrl     = "http://127.0.0.1:8000/api/webhook/signal"; // Copier Webhook URL
input string   InpAuthToken     = "davidsonsfx-token";                        // Authorization Token
input int      InpTimeoutMs     = 2000;                                        // HTTP Timeout (ms)

input group "=== Filter Settings ==="
input bool     InpFilterMagic   = false;  // Filter by Magic Number
input ulong    InpTargetMagic   = 0;      // Target Magic Number (if filter enabled)
input string   InpFilterSymbols = "";     // Filter Symbols (comma-separated, empty = all)

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("=================================================");
   Print("  DAVIDSONSFX TRADING COPIER - MASTER TRANSMITTER");
   Print("  Connected to: ", InpServerUrl);
   Print("=================================================");

   // Check if WebRequest is permitted
   char postData[];
   char result[];
   string resultHeaders;
   string testUrl = InpServerUrl;
   
   ResetLastError();
   int res = WebRequest("GET", "http://127.0.0.1:8000/api/health", "", InpTimeoutMs, postData, result, resultHeaders);
   if(res == -1)
   {
      int err = GetLastError();
      if(err == 4014) // ERR_WEBREQUEST_CANNOT_CONNECT
      {
         Print("WARNING: WebRequest URL not allowed in MT5 options!");
         Print("Please add 'http://127.0.0.1:8000' in Tools -> Options -> Expert Advisors -> Allow WebRequest for listed URL");
      }
   }
   else
   {
      Print("DavidsonsFX Server connection test SUCCESSFUL!");
   }

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("DavidsonsFX Master Transmitter unloaded.");
}

//+------------------------------------------------------------------+
//| Trade Transaction Event Handler                                  |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   // 1. Position Open & Close Events via Deals
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      ulong deal_ticket = trans.deal;
      if(HistoryDealSelect(deal_ticket))
      {
         long deal_entry = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
         long deal_type  = HistoryDealGetInteger(deal_ticket, DEAL_TYPE);
         ulong pos_id    = HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);
         ulong magic     = HistoryDealGetInteger(deal_ticket, DEAL_MAGIC);
         string symbol   = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
         double volume   = HistoryDealGetDouble(deal_ticket, DEAL_VOLUME);
         double price    = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);

         if(InpFilterMagic && magic != InpTargetMagic) return;
         if(!IsSymbolAllowed(symbol)) return;

         // Open Deal
         if(deal_entry == DEAL_ENTRY_IN)
         {
            string order_type = (deal_type == DEAL_TYPE_BUY) ? "BUY" : "SELL";
            double sl = 0.0, tp = 0.0;

            if(PositionSelectByTicket(pos_id))
            {
               sl = PositionGetDouble(POSITION_SL);
               tp = PositionGetDouble(POSITION_TP);
            }

            SendSignal("OPEN", pos_id, symbol, order_type, volume, price, sl, tp, 0.0, magic);
         }
         // Close Deal
         else if(deal_entry == DEAL_ENTRY_OUT || deal_entry == DEAL_ENTRY_INOUT)
         {
            string order_type = (deal_type == DEAL_TYPE_SELL) ? "BUY" : "SELL";
            SendSignal("CLOSE", pos_id, symbol, order_type, volume, price, 0.0, 0.0, volume, magic);
         }
      }
   }
   // 2. Stop Loss & Take Profit Modification Events
   else if(trans.type == TRADE_TRANSACTION_POSITION)
   {
      ulong pos_ticket = trans.position;
      if(PositionSelectByTicket(pos_ticket))
      {
         string symbol     = PositionGetString(POSITION_SYMBOL);
         long   pos_type   = PositionGetInteger(POSITION_TYPE);
         double volume     = PositionGetDouble(POSITION_VOLUME);
         double price      = PositionGetDouble(POSITION_PRICE_OPEN);
         double sl         = PositionGetDouble(POSITION_SL);
         double tp         = PositionGetDouble(POSITION_TP);
         ulong  magic      = PositionGetInteger(POSITION_MAGIC);

         string order_type = (pos_type == POSITION_TYPE_BUY) ? "BUY" : "SELL";
         SendSignal("MODIFY", pos_ticket, symbol, order_type, volume, price, sl, tp, 0.0, magic);
      }
   }
}

//+------------------------------------------------------------------+
//| Helper: Send JSON Payload to DavidsonsFX Copier Server           |
//+------------------------------------------------------------------+
void SendSignal(string action, ulong ticket, string symbol, string order_type, 
                double volume, double price, double sl, double tp, double close_volume, ulong magic)
{
   string json = StringFormat(
      "{\"action\":\"%s\",\"master_ticket\":%I64u,\"symbol\":\"%s\",\"order_type\":\"%s\",\"volume\":%.2f,\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"close_volume\":%.2f,\"magic\":%I64u,\"comment\":\"DavidsonsFX Master\"}",
      action, ticket, symbol, order_type, volume, price, sl, tp, close_volume, magic
   );

   char postData[];
   StringToCharArray(json, postData, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(postData, ArraySize(postData) - 1); // remove null terminator

   string headers = "Content-Type: application/json\r\nAuthorization: Bearer " + InpAuthToken + "\r\n";
   char result[];
   string resultHeaders;

   ResetLastError();
   int res = WebRequest("POST", InpServerUrl, headers, InpTimeoutMs, postData, result, resultHeaders);
   if(res == -1)
   {
      PrintFormat("[DavidsonsFX Error] Failed to transmit signal %s #%I64u. Error code: %d", action, ticket, GetLastError());
   }
   else
   {
      PrintFormat("[DavidsonsFX Sent] %s #%I64u %s %.2f @ %.5f (Server response: %d)", action, ticket, symbol, volume, price, res);
   }
}

//+------------------------------------------------------------------+
//| Helper: Check if Symbol is Allowed                               |
//+------------------------------------------------------------------+
bool IsSymbolAllowed(string symbol)
{
   if(StringLen(InpFilterSymbols) == 0) return true;
   return(StringFind(InpFilterSymbols, symbol) >= 0);
}

