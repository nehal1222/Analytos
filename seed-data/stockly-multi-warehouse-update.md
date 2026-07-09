# Stockly — Product Overview

**Product:** Stockly
**Category:** AI-powered inventory & demand forecasting for retail and e-commerce
**Owner:** Analytos, Retail Vertical

## Summary

Stockly plugs into a retailer's POS, ERP, and e-commerce platforms to forecast
demand at the SKU x location level, then automates replenishment so stores and
warehouses stop guessing. It's built for mid-market retail and e-commerce
chains (50–2,000 stores) who have outgrown spreadsheets but can't justify a
seven-figure enterprise planning suite.

## Features

- **Demand Forecasting Engine** — SKU x location forecasts refreshed daily,
  blending historical sell-through, seasonality, local events, and price
  elasticity. Forecast accuracy improved from a 62% baseline (naive
  moving-average forecasting) to 89% across our pilot cohort.
- **Auto-Replenishment** — Generates purchase orders automatically against
  forecast + safety stock targets, with human approval thresholds configurable
  per category.
- **Multi-Channel Sync** — Keeps on-hand inventory numbers consistent across
  physical stores, Shopify/BigCommerce storefronts, and marketplaces
  (Amazon, Walmart Marketplace) in near-real-time (sub-90-second sync lag).
- **Stockout Alerts** — Predictive alerts fire 5–7 days before a projected
  stockout, not after it happens, so planners can expedite or reallocate.
- **Warehouse Slotting Optimizer** — Recommends bin/slot placement changes
  based on pick frequency, cutting average pick-path distance.
- **Multi-Warehouse Inventory** — Pools stock levels across multiple
  distribution centers and routes each order from whichever warehouse
  minimizes shipping distance and cost, instead of a single fixed
  fulfillment location per customer region. Built for the first wave of
  Enterprise Retail customers running 3+ regional warehouses.

## Proof Points

- Pilot retailers saw **stockouts drop by 34%** within the first two full
  replenishment cycles (roughly 10 weeks).
- **Excess inventory carrying costs fell 21%** as auto-replenishment
  tightened safety stock instead of over-ordering "just in case."
- **Forecast accuracy rose from 62% to 89%** versus each customer's prior
  method (moving average or manual spreadsheet forecasting).
- Customers reach **positive ROI in 3.5 months on average**, driven mostly by
  the carrying-cost reduction plus fewer expedited-freight stockout rescues.
- Multi-Channel Sync reduced oversell incidents (selling inventory that was
  already sold on another channel) by **89%** in the first pilot cohort.
- Early Multi-Warehouse Inventory customers **reduced shipping costs by 15%**
  by routing orders to the nearest warehouse with stock on hand instead of a
  single default fulfillment center.

## Roadmap Decision Log

- **2026-04-02** — Decided to prioritize Multi-Channel Sync hardening over
  building new marketplace integrations (e.g. TikTok Shop) this quarter,
  after pilot feedback showed sync-lag complaints outweighed requests for new
  channels. Decision owned by Product; input from the Stockly pilot thread
  with our first retail customer.
- **2026-05-14** — Decided to ship configurable auto-replenishment approval
  thresholds per category (rather than a single global threshold) after
  planners asked to keep tighter manual control over high-cost SKUs.
- **2026-07-01** — Decided to launch Multi-Warehouse Inventory as an
  Enterprise Retail add-on rather than a mid-market default, since the
  3+ warehouse minimum only applies to a small slice of the existing
  customer base but matches every Enterprise Retail prospect in the current
  pipeline.

## Target Users

Stockly is sold to **Inventory Planning Managers** and **VP/Directors of
Supply Chain** at mid-market retail and e-commerce companies. Multi-Warehouse
Inventory additionally targets **Enterprise Retail** operations teams running
distributed fulfillment networks.
