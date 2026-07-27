from typing import List, Dict, Any, Tuple

def filter_lines_by_region(
    rect: Tuple[float, float, float, float],
    lines: List[Dict[str, Any]],
    overlap_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    ユーザーが選択した矩形範囲に基づいて、OCR結果の行リストをフィルタリングする。
    元の順序を保ったまま、条件を満たす行のみを返す。
    
    Args:
        rect: 選択矩形 (x1, y1, x2, y2)。x1 <= x2, y1 <= y2 を想定。
        lines: OCR結果の行リスト。各要素は "bbox" (x1, y1, x2, y2) を含む dict。
        overlap_threshold: 行の面積に対する重なり面積の割合の閾値（デフォルト0.5、すなわち50%以上）。
                           この閾値を採用した理由は、行の半分以上が選択範囲に含まれていれば、
                           ユーザーがその行を選択する意図があったとみなすためである。
                           
    Returns:
        条件を満たす行のリスト。
    """
    rx1, ry1, rx2, ry2 = rect
    
    # 矩形の座標が逆転している場合は補正する
    rx1, rx2 = min(rx1, rx2), max(rx1, rx2)
    ry1, ry2 = min(ry1, ry2), max(ry1, ry2)
    
    filtered_lines = []
    
    for line in lines:
        lx1, ly1, lx2, ly2 = line["bbox"]
        
        # 線の座標が逆転している場合は補正する（元のデータは変更しない）
        nx1, nx2 = min(lx1, lx2), max(lx1, lx2)
        ny1, ny2 = min(ly1, ly2), max(ly1, ly2)
        
        line_w = nx2 - nx1
        line_h = ny2 - ny1
        line_area = line_w * line_h
        
        # 退化したbbox（幅0または高さ0、すなわち面積0）の処理
        if line_area == 0:
            # 面積0の場合、重なり割合を計算しようとすると0除算が発生する。
            # 強制的に面積を1に水増しするなどのデータ改変は行わず、
            # 「選択矩形に完全に内包される場合のみ含める」というルールで判定する。
            is_contained = (rx1 <= nx1 <= rx2) and (rx1 <= nx2 <= rx2) and \
                           (ry1 <= ny1 <= ry2) and (ry1 <= ny2 <= ry2)
            if is_contained:
                filtered_lines.append(line)
        else:
            # 重なり矩形の計算
            overlap_w = max(0.0, min(rx2, nx2) - max(rx1, nx1))
            overlap_h = max(0.0, min(ry2, ny2) - max(ry1, ny1))
            overlap_area = overlap_w * overlap_h
            
            # 重なり面積が行の面積の指定閾値（デフォルト50%）以上であれば採用する
            if (overlap_area / line_area) >= overlap_threshold:
                filtered_lines.append(line)
                
    return filtered_lines
