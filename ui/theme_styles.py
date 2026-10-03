"""Translate FluidCursor's explicit dark QSS into a coherent light palette."""
import re

_LIGHT = {
    '#2b2b2b':'#FFFFFF', '#25292f':'#EDF3F8', '#414852':'#CBD5E1',
    '#24232d':'#F1EEF7', '#464050':'#D8D2E4', '#302f39':'#FFFFFF',
    '#484650':'#D6DCE5', '#3a3846':'#E7ECF4', '#343241':'#E9E2F7',
    '#777582':'#8B95A5', '#292830':'#F3F5F8', '#34323d':'#DCE2E9',
    '#292c36':'#F1EFF8', '#48465a':'#CBD0DF', '#343044':'#EDE7F8',
    '#62567e':'#C0B3D9', '#493b63':'#DFD4F0', '#312942':'#D5CAE9',
    '#29263d':'#F2ECFC', '#203332':'#E7F4F0', '#2e746e':'#148275',
    '#f3f6fc':'#1C2A3B', '#aebccc':'#516277', '#e6f7ff':'#182B41',
    '#aac1d5':'#5A6C80', '#f4f5f8':'#17293B', '#a6afbd':'#53657A',
    '#f7f5ff':'#26334A', '#b8b1cb':'#5C6A82', '#dbdae6':'#29394C',
    '#f1f5f9':'#192B3E', '#e4e7f4':'#273751', '#d5c6ff':'#604994',
    '#d9cdff':'#5B4398', '#91e5d0':'#117C66', '#d6d1e4':'#40516A',
    '#ffffff':'#25364B', '#64748b':'#8998AA', '#475569':'#B6C4D4',
    '#334155':'#CAD6E3', '#1e293b':'#879CB1', '#38bdf8':'#006B9A',
    '#58dabf':'#098A73', '#e3b66a':'#9A5A12', '#ef4444':'#B52438',
}
_LIGHT.update({
    '#73cfd9':'#087F8B', '#b9a4ff':'#6551AF', '#4ecfff':'#00749D',
    '#ffa96b':'#AE5924', '#ee99ca':'#A13F79', '#75d4ba':'#107B61',
    '#f7c56f':'#946315', '#7c6af2':'#6B50D6',
})
_HEX = re.compile(r'#[0-9a-fA-F]{6}\b')


def light_css(css):
    """Transform only known application-owned colors; preserve Qt Fluent QSS."""
    result = _HEX.sub(lambda match: _LIGHT.get(match.group().lower(), match.group()), css)
    result = result.replace('rgba(255, 255, 255,', 'rgba(15, 35, 59,')
    result = result.replace('rgba(56, 189, 248,', 'rgba(0, 107, 154,')
    result = result.replace('rgba(239, 68, 68,', 'rgba(170, 42, 56,')
    return result


def theme_css(css, is_light):
    return light_css(css) if is_light else css
