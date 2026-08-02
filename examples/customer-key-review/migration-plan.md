# Migration plan for `analytics.customer_360`

Risk score: **100/100**

## Before merge

- [ ] Add `customer_key` alongside `customer_id` and backfill it.
- [ ] Keep the old field available for one compatibility window.
- [ ] Update DataHub descriptions, tags, and ownership notes.
- [ ] Notify **Business Intelligence**
- [ ] Notify **Finance Analytics**
- [ ] Notify **Growth Engineering**
- [ ] Notify **Lifecycle ML**

## Consumer migration

- [ ] Update `finance.monthly_revenue`
- [ ] Update `ml.churn_features`
- [ ] Update `growth.campaign_segments`
- [ ] Update `executive.revenue_overview`

## Cutover

- [ ] Confirm downstream freshness and quality assertions are green.
- [ ] Remove `customer_id` only after every owner acknowledges the change.
