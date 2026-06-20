export interface CostBreakdown {
  retailPrice: number;
  printifyCost: number;
  shopifyTxnFee: number;
  paymentProcessingFee: number;
  totalCogs: number;
  netProfit: number;
  netMargin: number;
}

const SHOPIFY_CC_RATE = 0.029;
const SHOPIFY_CC_FLAT = 0.30;
const SHOPIFY_TXN_RATE = 0.0; // 0% when using Shopify Payments

export function calculateCostBreakdown(retailPrice: number, printifyCost: number): CostBreakdown {
  const paymentProcessingFee = retailPrice * SHOPIFY_CC_RATE + SHOPIFY_CC_FLAT;
  const shopifyTxnFee = retailPrice * SHOPIFY_TXN_RATE;
  const totalCogs = printifyCost + paymentProcessingFee + shopifyTxnFee;
  const netProfit = retailPrice - totalCogs;
  const netMargin = retailPrice > 0 ? (netProfit / retailPrice) * 100 : 0;

  return {
    retailPrice,
    printifyCost,
    shopifyTxnFee,
    paymentProcessingFee,
    totalCogs,
    netProfit,
    netMargin,
  };
}
