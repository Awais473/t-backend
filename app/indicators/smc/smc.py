import statistics
from app.indicators.base import BaseIndicator, IndicatorResult
from app.indicators.smc.smc_types import Pivot, OrderBlock, FVG, EqualLevel, StructureLine, TrailingExtremes


class SMCAIndicator(BaseIndicator):
    BULLISH = 1
    BEARISH = -1
    BULLISH_LEG = 1
    BEARISH_LEG = 0

    def __init__(self):
        super().__init__()
        self.name = "smc"

    @property
    def description(self) -> str:
        return "Smart Money Concepts [LuxAlgo]"

    def calculate(self, candles: list[dict], **params) -> IndicatorResult:
        swing_length = int(params.get("swing_length", 50))
        show_internals = params.get("show_internals", True)
        show_swing = params.get("show_swing", True)
        show_internal_ob = params.get("show_internal_ob", True)
        show_swing_ob = params.get("show_swing_ob", False)
        internal_ob_count = int(params.get("internal_ob_count", 5))
        swing_ob_count = int(params.get("swing_ob_count", 5))
        ob_filter = params.get("ob_filter", "atr")
        ob_mitigation = params.get("ob_mitigation", "high_low")
        show_fvg = params.get("show_fvg", False)
        fvg_threshold = params.get("fvg_threshold", True)
        show_eqh_eql = params.get("show_eqh_eql", True)
        eqh_eql_length = int(params.get("eqh_eql_length", 3))
        eqh_eql_threshold = float(params.get("eqh_eql_threshold", 0.1))
        show_swing_points = params.get("show_swing_points", False)
        show_zones = params.get("show_zones", False)
        show_strong_weak = params.get("show_strong_weak", True)
        show_mtf = params.get("show_mtf", False)
        show_trend_candles = params.get("show_trend_candles", False)

        n = len(candles)
        if n < max(swing_length, 20) + 5:
            return IndicatorResult("SMC", [], params)

        opens = [c["open"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        times = [self._to_seconds(c["timestamp"]) for c in candles]

        atr_values = self._compute_atr(highs, lows, closes, 200)
        atr = atr_values[-1] if atr_values else 0
        volatility_measure = atr

        parsed_highs: list[float] = []
        parsed_lows: list[float] = []
        raw_highs: list[float] = []
        raw_lows: list[float] = []
        raw_times: list[int] = []

        swing_high = Pivot()
        swing_low = Pivot()
        internal_high = Pivot()
        internal_low = Pivot()
        equal_high = Pivot()
        equal_low = Pivot()

        swing_trend = 0
        internal_trend = 0

        swing_obs: list[OrderBlock] = []
        internal_obs: list[OrderBlock] = []
        fvg_list: list[FVG] = []
        eqh_eql_list: list[EqualLevel] = []
        structure_lines: list[StructureLine] = []
        swing_point_list: list[dict] = []

        trailing = TrailingExtremes()

        prev_leg = self.BEARISH_LEG
        prev_internal_leg = self.BEARISH_LEG

        for i in range(n):
            if highVolatilityBar(highs, lows, i, volatility_measure):
                parsed_highs.append(lows[i])
                parsed_lows.append(highs[i])
            else:
                parsed_highs.append(highs[i])
                parsed_lows.append(lows[i])
            raw_highs.append(highs[i])
            raw_lows.append(lows[i])
            raw_times.append(times[i])

            if i < swing_length + 1:
                if i == 0:
                    swing_high.current_level = highs[i]
                    swing_low.current_level = lows[i]
                    internal_high.current_level = highs[i]
                    internal_low.current_level = lows[i]
                    trailing.top = highs[i]
                    trailing.bottom = lows[i]
                    trailing.bar_time = times[i]
                    trailing.bar_index = i
                s_leg = detect_leg(highs, lows, i, min(i, swing_length))
                if s_leg is not None:
                    prev_leg = s_leg
                i_leg = detect_leg(highs, lows, i, min(i, 5))
                if i_leg is not None:
                    prev_internal_leg = i_leg
                continue

            s_leg = detect_leg(highs, lows, i, swing_length)
            if s_leg is not None:
                new_pivot = s_leg != prev_leg
                pivot_low = s_leg - prev_leg == 1
                pivot_high = s_leg - prev_leg == -1

                if new_pivot:
                    if pivot_low:
                        if show_eqh_eql and abs(equal_low.current_level - lows[i - swing_length]) < eqh_eql_threshold * atr:
                            eqh_eql_list.append(EqualLevel(
                                price=equal_low.current_level,
                                bar_time=equal_low.bar_time,
                                bar_index=equal_low.bar_index,
                                matched_price=lows[i - swing_length],
                                matched_time=times[i - swing_length],
                                matched_index=i,
                                is_high=False,
                            ))

                        equal_low.last_level = equal_low.current_level
                        equal_low.current_level = lows[i - swing_length]
                        equal_low.crossed = False
                        equal_low.bar_time = times[i - swing_length]
                        equal_low.bar_index = i - swing_length

                        swing_low.last_level = swing_low.current_level
                        swing_low.current_level = lows[i - swing_length]
                        swing_low.crossed = False
                        swing_low.bar_time = times[i - swing_length]
                        swing_low.bar_index = i - swing_length

                        trailing.bottom = swing_low.current_level
                        trailing.bar_time = swing_low.bar_time
                        trailing.bar_index = swing_low.bar_index
                        trailing.last_bottom_time = swing_low.bar_time

                        if show_swing_points:
                            label = "LL" if swing_low.current_level < swing_low.last_level else "HL"
                            swing_point_list.append({
                                "time": times[i - swing_length],
                                "price": lows[i - swing_length],
                                "type": label,
                                "bias": "bullish",
                            })
                    else:
                        if show_eqh_eql and abs(equal_high.current_level - highs[i - swing_length]) < eqh_eql_threshold * atr:
                            eqh_eql_list.append(EqualLevel(
                                price=equal_high.current_level,
                                bar_time=equal_high.bar_time,
                                bar_index=equal_high.bar_index,
                                matched_price=highs[i - swing_length],
                                matched_time=times[i - swing_length],
                                matched_index=i,
                                is_high=True,
                            ))

                        equal_high.last_level = equal_high.current_level
                        equal_high.current_level = highs[i - swing_length]
                        equal_high.crossed = False
                        equal_high.bar_time = times[i - swing_length]
                        equal_high.bar_index = i - swing_length

                        swing_high.last_level = swing_high.current_level
                        swing_high.current_level = highs[i - swing_length]
                        swing_high.crossed = False
                        swing_high.bar_time = times[i - swing_length]
                        swing_high.bar_index = i - swing_length

                        trailing.top = swing_high.current_level
                        trailing.bar_time = swing_high.bar_time
                        trailing.bar_index = swing_high.bar_index
                        trailing.last_top_time = swing_high.bar_time

                        if show_swing_points:
                            label = "HH" if swing_high.current_level > swing_high.last_level else "LH"
                            swing_point_list.append({
                                "time": times[i - swing_length],
                                "price": highs[i - swing_length],
                                "type": label,
                                "bias": "bearish",
                            })

                prev_leg = s_leg

            i_leg = detect_leg(highs, lows, i, 5)
            if i_leg is not None:
                new_internal_pivot = i_leg != prev_internal_leg
                internal_pivot_low = i_leg - prev_internal_leg == 1
                internal_pivot_high = i_leg - prev_internal_leg == -1

                if new_internal_pivot:
                    if internal_pivot_low:
                        internal_low.last_level = internal_low.current_level
                        internal_low.current_level = lows[i - 5]
                        internal_low.crossed = False
                        internal_low.bar_time = times[i - 5]
                        internal_low.bar_index = i - 5
                    else:
                        internal_high.last_level = internal_high.current_level
                        internal_high.current_level = highs[i - 5]
                        internal_high.crossed = False
                        internal_high.bar_time = times[i - 5]
                        internal_high.bar_index = i - 5

                prev_internal_leg = i_leg

            bullish_bar = (highs[i] - max(closes[i], opens[i])) > (min(closes[i], opens[i]) - lows[i])
            bearish_bar = (highs[i] - max(closes[i], opens[i])) < (min(closes[i], opens[i]) - lows[i])

            if show_swing or show_swing_ob:
                extra_cond = True
                if closes[i] > swing_high.current_level and not swing_high.crossed and extra_cond and swing_high.current_level != 0:
                    tag = "CHoCH" if swing_trend == self.BEARISH else "BOS"
                    swing_high.crossed = True
                    swing_trend = self.BULLISH
                    structure_lines.append(StructureLine(
                        price=swing_high.current_level,
                        bar_time=swing_high.bar_time,
                        bar_index=swing_high.bar_index,
                        tag=tag,
                        bias=self.BULLISH,
                        is_internal=False,
                    ))
                    if show_swing_ob:
                        store_order_block(parsed_highs, parsed_lows, raw_times, swing_obs, swing_high, self.BULLISH, i, swing_ob_count)

                extra_cond = True
                if closes[i] < swing_low.current_level and not swing_low.crossed and extra_cond and swing_low.current_level != 0:
                    tag = "CHoCH" if swing_trend == self.BULLISH else "BOS"
                    swing_low.crossed = True
                    swing_trend = self.BEARISH
                    structure_lines.append(StructureLine(
                        price=swing_low.current_level,
                        bar_time=swing_low.bar_time,
                        bar_index=swing_low.bar_index,
                        tag=tag,
                        bias=self.BEARISH,
                        is_internal=False,
                    ))
                    if show_swing_ob:
                        store_order_block(parsed_highs, parsed_lows, raw_times, swing_obs, swing_low, self.BEARISH, i, swing_ob_count)

            if show_internals or show_internal_ob:
                extra_cond_int = internal_high.current_level != swing_high.current_level and bullish_bar
                if closes[i] > internal_high.current_level and not internal_high.crossed and extra_cond_int and internal_high.current_level != 0:
                    tag = "CHoCH" if internal_trend == self.BEARISH else "BOS"
                    internal_high.crossed = True
                    internal_trend = self.BULLISH
                    structure_lines.append(StructureLine(
                        price=internal_high.current_level,
                        bar_time=internal_high.bar_time,
                        bar_index=internal_high.bar_index,
                        tag=tag,
                        bias=self.BULLISH,
                        is_internal=True,
                    ))
                    if show_internal_ob:
                        store_order_block(parsed_highs, parsed_lows, raw_times, internal_obs, internal_high, self.BULLISH, i, internal_ob_count)

                extra_cond_int = internal_low.current_level != swing_low.current_level and bearish_bar
                if closes[i] < internal_low.current_level and not internal_low.crossed and extra_cond_int and internal_low.current_level != 0:
                    tag = "CHoCH" if internal_trend == self.BULLISH else "BOS"
                    internal_low.crossed = True
                    internal_trend = self.BEARISH
                    structure_lines.append(StructureLine(
                        price=internal_low.current_level,
                        bar_time=internal_low.bar_time,
                        bar_index=internal_low.bar_index,
                        tag=tag,
                        bias=self.BEARISH,
                        is_internal=True,
                    ))
                    if show_internal_ob:
                        store_order_block(parsed_highs, parsed_lows, raw_times, internal_obs, internal_low, self.BEARISH, i, internal_ob_count)

            max_ob_mit = highs[i] if ob_mitigation == "high_low" else closes[i]
            min_ob_mit = lows[i] if ob_mitigation == "high_low" else closes[i]
            mitigate_order_blocks(swing_obs, max_ob_mit, min_ob_mit)
            mitigate_order_blocks(internal_obs, max_ob_mit, min_ob_mit)

            trailing.top = max(highs[i], trailing.top)
            if trailing.top == highs[i]:
                trailing.last_top_time = times[i]
            trailing.bottom = min(lows[i], trailing.bottom)
            if trailing.bottom == lows[i]:
                trailing.last_bottom_time = times[i]

        if show_fvg:
            fvg_list = self._detect_fvgs(opens, highs, lows, closes, times, fvg_threshold)

        ob_data = {"internal": [], "swing": []}
        for ob in internal_obs[:internal_ob_count]:
            ob_data["internal"].append({
                "start_time": ob.bar_time,
                "end_time": times[-1],
                "high": ob.bar_high,
                "low": ob.bar_low,
                "bias": "bullish" if ob.bias == self.BULLISH else "bearish",
            })
        for ob in swing_obs[:swing_ob_count]:
            ob_data["swing"].append({
                "start_time": ob.bar_time,
                "end_time": times[-1],
                "high": ob.bar_high,
                "low": ob.bar_low,
                "bias": "bullish" if ob.bias == self.BULLISH else "bearish",
            })

        struct_data = {"internal": [], "swing": []}
        for sl in structure_lines:
            target = "internal" if sl.is_internal else "swing"
            bias_str = "bullish" if sl.bias == self.BULLISH else "bearish"
            struct_data[target].append({
                "time": sl.bar_time,
                "price": sl.price,
                "tag": sl.tag,
                "bias": bias_str,
            })

        eqh_eql_data = []
        for eq in eqh_eql_list:
            eqh_eql_data.append({
                "time": eq.bar_time,
                "price": eq.price,
                "matched_time": eq.matched_time,
                "matched_price": eq.matched_price,
                "type": "EQH" if eq.is_high else "EQL",
            })

        fvg_data = []
        for fvg in fvg_list:
            fvg_data.append({
                "start_time": fvg.start_time,
                "end_time": fvg.end_time,
                "top": fvg.top,
                "bottom": fvg.bottom,
                "bias": "bullish" if fvg.bias == self.BULLISH else "bearish",
            })

        sw = {
            "strong_high": {"price": trailing.top, "time": trailing.last_top_time},
            "weak_high": {"price": trailing.top, "time": trailing.last_top_time},
            "strong_low": {"price": trailing.bottom, "time": trailing.last_bottom_time},
            "weak_low": {"price": trailing.bottom, "time": trailing.last_bottom_time},
        }
        if swing_trend == self.BULLISH:
            sw["weak_high"]["price"] = trailing.bottom
            sw["strong_low"]["price"] = trailing.bottom
        else:
            sw["strong_high"]["price"] = trailing.top
            sw["weak_low"]["price"] = trailing.top

        eq_lvl = (trailing.top + trailing.bottom) / 2
        zones = {
            "premium": {"top": trailing.top, "bottom": 0.95 * trailing.top + 0.05 * trailing.bottom},
            "equilibrium": {"price": eq_lvl},
            "discount": {"top": 0.95 * trailing.bottom + 0.05 * trailing.top, "bottom": trailing.bottom},
        }

        mtf_levels = {}
        if show_mtf:
            mtf_levels = self._compute_mtf_levels(candles)

        candle_colors = []
        if show_trend_candles:
            base_color = "#089981" if swing_trend == self.BULLISH else "#F23645"
            candle_colors = [{"time": t, "color": base_color} for t in times]

        result_data = [{
            "trend": "bullish" if swing_trend == self.BULLISH else "bearish",
            "internal_trend": "bullish" if internal_trend == self.BULLISH else "bearish",
            "structures": struct_data,
            "order_blocks": ob_data,
            "fvgs": fvg_data,
            "eqh_eql": eqh_eql_data,
            "swing_points": swing_point_list,
            "strong_weak": sw,
            "zones": zones,
            "mtf_levels": mtf_levels,
            "candle_colors": candle_colors,
        }]

        return IndicatorResult("SMC", result_data, params)

    def _detect_fvgs(self, opens, highs, lows, closes, times, auto_threshold) -> list[FVG]:
        fvg_list = []
        n = len(closes)
        if n < 5:
            return fvg_list

        total_delta = 0.0
        count = 0
        for i in range(2, n):
            prev_close = closes[i - 2]
            prev_open = opens[i - 2]
            bar_delta = (prev_close - prev_open) / (prev_open * 100) if prev_open != 0 else 0
            total_delta += abs(bar_delta)
            count += 1
        avg_delta = (total_delta / count * 2) if count > 0 else 0

        interval = times[1] - times[0] if len(times) > 1 else 3600

        for i in range(4, n):
            prev_close = closes[i - 1]
            prev_open = opens[i - 1]
            bar_delta = (prev_close - prev_open) / (prev_open * 100) if prev_open != 0 else 0
            threshold = avg_delta if auto_threshold else 0

            if lows[i] > highs[i - 2] and closes[i - 1] > highs[i - 2] and bar_delta > threshold:
                fvg_list.append(FVG(
                    top=lows[i],
                    bottom=highs[i - 2],
                    bias=self.BULLISH,
                    start_time=times[i - 2],
                    end_time=times[i] + interval,
                ))
            if highs[i] < lows[i - 2] and closes[i - 1] < lows[i - 2] and -bar_delta > threshold:
                fvg_list.append(FVG(
                    top=highs[i],
                    bottom=lows[i - 2],
                    bias=self.BEARISH,
                    start_time=times[i - 2],
                    end_time=times[i] + interval,
                ))

        return fvg_list

    def _compute_mtf_levels(self, candles: list[dict]) -> dict:
        result = {}
        timeframes = {"daily": 86400, "weekly": 604800, "monthly": 2592000}
        for tf_name, tf_seconds in timeframes.items():
            tf_candles = []
            for c in candles:
                ts = self._to_seconds(c["timestamp"])
                tf_key = ts // tf_seconds
                tf_candles.append((tf_key, c["high"], c["low"], ts))
            if tf_candles:
                groups = {}
                for key, high, low, ts in tf_candles:
                    if key not in groups:
                        groups[key] = {"high": high, "low": low, "time": ts}
                    else:
                        groups[key]["high"] = max(groups[key]["high"], high)
                        groups[key]["low"] = min(groups[key]["low"], low)
                        groups[key]["time"] = max(groups[key]["time"], ts)
                keys = sorted(groups.keys())
                if len(keys) >= 2:
                    last = groups[keys[-2]]
                    result[tf_name] = {
                        "high": {"price": round(last["high"], 2), "time": last["time"]},
                        "low": {"price": round(last["low"], 2), "time": last["time"]},
                    }
        return result

    @staticmethod
    def _compute_atr(highs, lows, closes, period):
        if len(highs) < 2:
            return [0]
        tr = [max(highs[0] - lows[0], abs(highs[0] - closes[0]))]
        for i in range(1, len(highs)):
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
        atr = [sum(tr[:period]) / period] if len(tr) >= period else [sum(tr) / len(tr)]
        for v in tr[period:]:
            atr.append((atr[-1] * (period - 1) + v) / period)
        return atr


def highVolatilityBar(highs, lows, i, volatility_measure, multiplier=2):
    if i < 0 or i >= len(highs) or volatility_measure <= 0:
        return False
    return (highs[i] - lows[i]) >= (multiplier * volatility_measure)


def detect_leg(highs, lows, i, size):
    if i < size + 1 or size < 2:
        return None
    period_highs = highs[i - size:i]
    period_lows = lows[i - size:i]
    is_new_high = highs[i - size] > max(period_highs[:-1]) if len(period_highs) > 1 else False
    is_new_low = lows[i - size] < min(period_lows[:-1]) if len(period_lows) > 1 else False
    if is_new_high:
        return 0
    if is_new_low:
        return 1
    return None


def store_order_block(parsed_highs, parsed_lows, raw_times, order_blocks, pivot, bias, current_index, max_count):
    if bias == -1:
        p_highs = parsed_highs[pivot.bar_index:current_index]
        p_lows = parsed_lows[pivot.bar_index:current_index]
        if not p_highs:
            return
        max_idx = p_highs.index(max(p_highs))
        parsed_idx = pivot.bar_index + max_idx
    else:
        p_highs = parsed_highs[pivot.bar_index:current_index]
        p_lows = parsed_lows[pivot.bar_index:current_index]
        if not p_lows:
            return
        min_idx = p_lows.index(min(p_lows))
        parsed_idx = pivot.bar_index + min_idx

    ob = OrderBlock(
        bar_high=parsed_highs[parsed_idx],
        bar_low=parsed_lows[parsed_idx],
        bar_time=raw_times[parsed_idx],
        bias=bias,
    )
    if len(order_blocks) >= 100:
        order_blocks.pop()
    order_blocks.insert(0, ob)


def mitigate_order_blocks(order_blocks, max_price, min_price):
    to_remove = []
    for i, ob in enumerate(order_blocks):
        if max_price > ob.bar_high and ob.bias == -1:
            to_remove.append(i)
        elif min_price < ob.bar_low and ob.bias == 1:
            to_remove.append(i)
    for idx in reversed(to_remove):
        order_blocks.pop(idx)
