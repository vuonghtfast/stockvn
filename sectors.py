# Sector mapping for Vietnamese stocks
# Phân loại ngành cho cổ phiếu Việt Nam

SECTOR_MAPPING = {
    # Ngân hàng (Banking)
    "VCB": "Ngân hàng",
    "TCB": "Ngân hàng",
    "MBB": "Ngân hàng",
    "VPB": "Ngân hàng",
    "ACB": "Ngân hàng",
    "CTG": "Ngân hàng",
    "BID": "Ngân hàng",
    "STB": "Ngân hàng",
    "HDB": "Ngân hàng",
    "TPB": "Ngân hàng",
    "SHB": "Ngân hàng",
    "EIB": "Ngân hàng",
    "MSB": "Ngân hàng",
    "OCB": "Ngân hàng",
    "VIB": "Ngân hàng",
    "LPB": "Ngân hàng",
    "SSB": "Ngân hàng",
    "BAB": "Ngân hàng",
    "NVB": "Ngân hàng",
    "ABB": "Ngân hàng",
    
    # Bất động sản (Real Estate)
    "VHM": "Bất động sản",
    "VIC": "Bất động sản",
    "NVL": "Bất động sản",
    "PDR": "Bất động sản",
    "DXG": "Bất động sản",
    "DIG": "Bất động sản",
    "NLG": "Bất động sản",
    "KDH": "Bất động sản",
    "HDG": "Bất động sản",
    "CEO": "Bất động sản",
    "BCM": "Bất động sản",
    "HDC": "Bất động sản",
    "KBC": "Bất động sản",
    "DXS": "Bất động sản",
    "SCR": "Bất động sản",
    "IDC": "Bất động sản",
    
    # Thép (Steel)
    "HPG": "Thép",
    "HSG": "Thép",
    "NKG": "Thép",
    "POM": "Thép",
    "TLH": "Thép",
    "VIS": "Thép",
    
    # Thực phẩm & Đồ uống (Food & Beverage)
    "VNM": "Thực phẩm",
    "MSN": "Thực phẩm",
    "SAB": "Thực phẩm",
    "VHC": "Thực phẩm",
    "MCH": "Thực phẩm",
    "KDC": "Thực phẩm",
    "QNS": "Thực phẩm",
    "SBT": "Thực phẩm",
    "LSS": "Thực phẩm",
    
    # Bán lẻ (Retail)
    "MWG": "Bán lẻ",
    "FRT": "Bán lẻ",
    "PNJ": "Bán lẻ",
    "DGW": "Bán lẻ",
    "VGC": "Bán lẻ",
    
    # Dầu khí (Oil & Gas)
    "GAS": "Dầu khí",
    "PLX": "Dầu khí",
    "PVD": "Dầu khí",
    "PVS": "Dầu khí",
    "PVT": "Dầu khí",
    "PVG": "Dầu khí",
    
    # Điện (Power)
    "POW": "Điện",
    "NT2": "Điện",
    "PC1": "Điện",
    "REE": "Điện",
    
    # Xây dựng (Construction)
    "CTD": "Xây dựng",
    "HBC": "Xây dựng",
    "FCN": "Xây dựng",
    "LCG": "Xây dựng",
    "HT1": "Xây dựng",
    "VCG": "Xây dựng",
    
    # Chứng khoán (Securities)
    "SSI": "Chứng khoán",
    "VCI": "Chứng khoán",
    "VND": "Chứng khoán",
    "HCM": "Chứng khoán",
    "FTS": "Chứng khoán",
    "MBS": "Chứng khoán",
    "VIX": "Chứng khoán",
    "AGR": "Chứng khoán",
    "SHS": "Chứng khoán",
    
    # Công nghệ (Technology)
    "FPT": "Công nghệ",
    "CMG": "Công nghệ",
    "VGI": "Công nghệ",
    "ITD": "Công nghệ",
    
    # Hàng không (Aviation)
    "HVN": "Hàng không",
    "VJC": "Hàng không",
    
    # Logistics
    "GMD": "Logistics",
    "HAH": "Logistics",
    "TCL": "Logistics",
    
    # Dược phẩm (Pharmaceutical)
    "DHG": "Dược phẩm",
    "DMC": "Dược phẩm",
    "IMP": "Dược phẩm",
    "DCL": "Dược phẩm",
    
    # Cao su (Rubber)
    "GVR": "Cao su",
    "DPR": "Cao su",
    "PHR": "Cao su",
    
    # Thủy sản (Seafood)
    "VHC": "Thủy sản",
    "ANV": "Thủy sản",
    "IDI": "Thủy sản",
    
    # Nông nghiệp (Agriculture)
    "HAG": "Nông nghiệp",
    "HNG": "Nông nghiệp",
    "SBT": "Nông nghiệp",
    
    # Vận tải (Transportation)
    "PVT": "Vận tải",
    "VSC": "Vận tải",
    "GMD": "Vận tải",
}

def get_sector(ticker):
    """Get sector for a ticker, return 'Khác' if not found"""
    return SECTOR_MAPPING.get(ticker.upper(), "Khác")

def get_all_sectors():
    """Get list of unique sectors"""
    sectors = list(set(SECTOR_MAPPING.values()))
    return sorted(sectors)

def get_tickers_by_sector(sector):
    """Get all tickers in a sector"""
    return [ticker for ticker, sec in SECTOR_MAPPING.items() if sec == sector]
