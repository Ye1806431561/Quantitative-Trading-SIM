# Task Checklist

## Phase 0: Scope & Foundation
- [x] 1. Establish requirements traceability checklist <!-- id: 0 -->
- [x] 2. Define minimum viable scope (MVP) <!-- id: 1 -->
- [x] 3. Create project directory structure & placeholders <!-- id: 2 -->
- [x] 4. Lock dependencies in requirements.txt <!-- id: 3 -->
- [x] 5. Create configuration templates <!-- id: 4 -->
- [x] 6. Implement configuration loading & validation <!-- id: 5 -->
- [x] 7. Design & implement logging scheme <!-- id: 6 -->

## Phase 1: Data Layer & Storage
- [x] 8. Design database connection lifecycle <!-- id: 7 -->
- [x] 9. Define & verify table structures <!-- id: 8 -->
- [x] 10. Define domain models & validation rules <!-- id: 9 -->
- [x] 11. Implement account initialization & balance management <!-- id: 10 -->
- [ ] 12. Implement order persistence interfaces <!-- id: 11 -->
- [ ] 13. Implement trade recording & order association <!-- id: 12 -->
- [ ] 14. Design market data fetch interfaces <!-- id: 13 -->
- [ ] 15. Implement historical candle download & storage <!-- id: 14 -->
- [ ] 16. Add historical data caching & deduplication <!-- id: 15 -->

## Phase 2: Matching, Risk & Market Data
- [ ] 17. Implement real-time market data fetching <!-- id: 16 -->
- [ ] 18. Implement pricing service <!-- id: 17 -->
- [ ] 19. Implement market order matching logic <!-- id: 18 -->
- [ ] 20. Implement limited order queue & matching <!-- id: 19 -->
- [ ] 21. Implement stop-loss/take-profit triggers <!-- id: 20 -->
- [ ] 22. Implement fee & slippage calculation <!-- id: 21 -->
- [ ] 23. Implement order state machine <!-- id: 22 -->
- [ ] 24. Implement risk control checks <!-- id: 23 -->

## Phase 3: Strategies & Dual Engines
- [ ] 25. Design strategy interface lifecycle <!-- id: 24 -->
- [ ] 26. Integrate Backtrader engine <!-- id: 25 -->
- [ ] 27. Mount standard analyzers <!-- id: 26 -->
- [ ] 28. Output backtest results <!-- id: 27 -->
- [ ] 29. Implement real-time simulation loop <!-- id: 28 -->
- [ ] 30. Implement strategy adapter <!-- id: 29 -->
- [ ] 31. Implement Dual MA strategy <!-- id: 30 -->
- [ ] 32. Implement Grid strategy <!-- id: 31 -->
- [ ] 33. Implement Bollinger Bands strategy <!-- id: 32 -->
- [ ] 34. Implement strategy parameter management <!-- id: 33 -->

## Phase 4: Interfaces, Monitoring & Quality
- [ ] 35. Implement performance analysis module <!-- id: 34 -->
- [ ] 36. Implement visualization output <!-- id: 35 -->
- [ ] 37. Implement CLI command set <!-- id: 36 -->
- [ ] 38. Implement operation status & monitoring <!-- id: 37 -->
- [ ] 39. Establish unit & integration test suites <!-- id: 38 -->
- [ ] 40. Perform performance benchmarking <!-- id: 39 -->
- [ ] 41. Update README & documentation <!-- id: 40 -->
- [ ] 42. Final regression check <!-- id: 41 -->
