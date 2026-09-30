/* Shared deterministic rules. No network, DOM, or AI assertions. */
(function (root) {
  'use strict';
  const number = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
  const taipei = now => new Date(now.getTime() + 8 * 3600000);
  function date(value, end = false) {
    const text = String(value || '').trim();
    const m = text.match(/^(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?(?:[T\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$/);
    if (!m) return null;
    const [y, mo, d] = m.slice(1, 4).map(Number);
    const h = m[4] === undefined ? (end ? 23 : 0) : +m[4];
    const mi = m[5] === undefined ? (end ? 59 : 0) : +m[5];
    const s = m[6] === undefined ? (end && m[4] === undefined ? 59 : 0) : +m[6];
    const check = new Date(Date.UTC(y, mo - 1, d));
    if (check.getUTCFullYear() !== y || check.getUTCMonth() !== mo - 1 || check.getUTCDate() !== d || h > 23 || mi > 59 || s > 59) return null;
    const pad = n => String(n).padStart(2, '0');
    const result = new Date(`${y}-${pad(mo)}-${pad(d)}T${pad(h)}:${pad(mi)}:${pad(s)}${m[7] || (end && m[4] === undefined ? '.999' : '')}${m[8] || '+08:00'}`);
    return Number.isNaN(+result) ? null : result;
  }
  function registrationWindow(rule) {
    if (rule.registrationStart || rule.registrationEnd) return {
      start: date(rule.registrationStart), end: date(rule.registrationEnd, true)
    };
    const text = String(rule.regDeadline || '');
    // Recurrence and abbreviated date ranges need explicit structured windows.
    if (/每月|每週|當月/.test(text)) return { start: null, end: null };
    const dates = [...text.matchAll(/20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?(?:[ T]\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?/g)].map(m => m[0]);
    if (dates.length === 2) return { start: date(dates[0]), end: date(dates[1], true) };
    if (dates.length === 1 && !/[~～至]/.test(text)) {
      if (/開放|開始|起/.test(text) && !/截止/.test(text)) return { start: date(dates[0]), end: null };
      return { start: null, end: date(dates[0], true) };
    }
    return { start: null, end: null };
  }
  function periodKey(rule, now = new Date()) {
    const t = taipei(now);
    const cycle = /每月|當月/.test(rule.regDeadline || '') || rule.registrationCycle === 'MONTHLY'
      ? `${t.getUTCFullYear()}-${t.getUTCMonth() + 1}` : '';
    return JSON.stringify([rule.id, rule.sourceUrl, rule.validFrom, rule.validUntil,
      rule.registrationStart, rule.registrationEnd, rule.regDeadline, cycle]);
  }
  function lifecycle(rule, now = new Date()) {
    const w = registrationWindow(rule);
    const end = date(rule.validUntil, true);
    if ((end && end < now) || (w.end && w.end < now)) return 'expired';
    if (w.start && w.start > now) return 'upcoming';
    if (rule.registered && rule.registeredPeriod === periodKey(rule, now)) return 'marked';
    return w.start && w.end ? 'available' : 'unknown';
  }
  function calculate(rule, amount) {
    const spendAmount = number(amount) || 0;
    const result = { effectiveRate: 0, potentialRate: 0, totalCash: 0, potentialCash: 0,
      spendAmount, isBoostActive: false, capped: false, capAmount: number(rule.capAmount),
      calculable: false, reason: '', assumptions: [] };
    const fail = reason => ({ ...result, reason });
    const type = String(rule.rewardType || '').toLowerCase();
    const unit = String(rule.rewardUnit || '').toLowerCase();
    if (['draw', 'installment', 'insurance_benefit'].includes(type)) return fail('非保證現金回饋');
    if (type === 'points' && unit !== 'percent' && unit !== 'twd') return fail('點數未確認兌換價值');
    const min = number(rule.minimumSpend);
    if (min !== null && spendAmount < min) return fail('本筆未達最低消費門檻');
    if (/累積|累計/.test(rule.quotaInfo || '') && rule.spendBasis !== 'PER_TRANSACTION') return fail('累積消費資格未確認');
    const base = number(rule.baseRate) || 0;
    const promo = number(rule.promoRate) || 0;
    const mode = rule.rewardCalculationMode;
    const tiers = (rule.rewardTiers || []).filter(t => number(t.totalRate) !== null && t.totalRate <= 100);
    let current = { totalRate: base + promo, baseRate: base, capAmount: rule.capAmount };
    let best = current;
    if (mode === 'TIERED') {
      if (!tiers.length) return fail('缺少分級條件');
      current = tiers.find(t => t.isDefault && !(t.requirements || []).length);
      best = [...tiers].sort((a, b) => b.totalRate - a.totalRate)[0];
      if (!current) result.assumptions.push('未確認適用資格，僅供達標情境試算');
    } else if (mode === 'MAX_ONLY') {
      result.potentialRate = Math.max(base, promo, unit === 'percent' ? number(rule.rewardAmount) || 0 : 0);
      return fail('最高回饋缺少可試算的一般資格');
    } else if (mode !== 'FLAT') return fail('回饋計算方式待確認');
    if (base > 100 || promo > 100 || best.totalRate > 100) return fail('回饋率異常');
    const fixed = type === 'cash' || (type === 'points' && unit === 'twd');
    if (fixed && (rule.spendBasis !== 'PER_TRANSACTION' || min === null || number(rule.rewardAmount) === null)) return fail('固定回饋門檻或計次方式未確認');
    if (rule.roundingMode !== 'FLOOR_COMPONENT' && rule.roundingMode !== 'FLOOR' && rule.roundingMode !== 'ROUND') result.assumptions.push('銀行取整方式待確認，金額僅為試算');
    const round = n => rule.roundingMode === 'ROUND' ? Math.round(n) : rule.roundingMode?.startsWith('FLOOR') ? Math.floor(n + 1e-9) : Math.floor((n + 1e-9) * 100) / 100;
    function cash(tier) {
      if (!tier) return 0;
      const total = tier.totalRate;
      const b = fixed ? 0 : Math.min(number(tier.baseRate) ?? base, total);
      let baseCash = spendAmount * b / 100;
      let bonusCash = fixed ? rule.rewardAmount : spendAmount * (total - b) / 100;
      const cap = number(tier.capAmount) ?? number(rule.capAmount);
      if (rule.roundingMode === 'FLOOR_COMPONENT') { baseCash = round(baseCash); bonusCash = round(bonusCash); }
      if (cap !== null) {
        if (!['PROMO', 'TOTAL', 'NONE'].includes(rule.capScope)) return null;
        if (rule.capScope !== 'NONE') {
          const remaining = number(rule.remainingCap);
          const limit = remaining === null ? cap : Math.min(cap, remaining);
          if (rule.capPeriod !== 'PER_TRANSACTION' && remaining === null) result.assumptions.push('假設本期回饋額度尚未使用');
          if (rule.capScope === 'TOTAL') { result.capped ||= baseCash + bonusCash > limit; return round(Math.min(baseCash + bonusCash, limit)); }
          result.capped ||= bonusCash > limit;
          bonusCash = Math.min(bonusCash, limit);
        }
      }
      return round(baseCash + bonusCash);
    }
    result.potentialRate = fixed ? 0 : best.totalRate;
    const potential = cash(best);
    if (potential === null) return fail('回饋上限適用範圍未確認');
    result.potentialCash = potential;
    const qualified = (!rule.needReg || (rule.registered && rule.registeredPeriod === periodKey(rule)))
      && !(rule.eligibilityRequirements || []).length && rule.selectionMode !== 'SWITCHABLE';
    result.effectiveRate = qualified && current ? current.totalRate : 0;
    result.totalCash = qualified && current ? cash(current) : 0;
    if (result.totalCash === null) return fail('一般資格上限待確認');
    result.isBoostActive = qualified && !!current;
    result.calculable = true;
    result.assumptions = [...new Set(result.assumptions)];
    return result;
  }
  function isReviewed(rule, now = new Date()) {
    const review = rule.accuracyReview;
    const checked = date(review?.checkedAt);
    return !!(review?.status === 'SOURCE_CHECKED' && !review.issues?.length
      && review.fields?.length && review.sourceUrl === rule.sourceUrl && checked
      && checked <= now && now - checked <= 14 * 86400000);
  }
  const api = { date, registrationWindow, periodKey, lifecycle, calculate, isReviewed };
  if (typeof module !== 'undefined') module.exports = api;
  else root.KanuAccuracy = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
