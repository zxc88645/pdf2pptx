// pdfjs-dist 5.x 使用 Map.prototype.getOrInsertComputed（較新的 JS 標準方法），
// 舊版瀏覽器沒有時會出現：
// TypeError: this[#methodPromises].getOrInsertComputed is not a function
// 需在載入 pdfjs-dist 的任何模組之前執行。
if (typeof Map !== 'undefined' && typeof Map.prototype.getOrInsertComputed !== 'function') {
  Map.prototype.getOrInsertComputed = function getOrInsertComputed(key, callbackFn) {
    if (this.has(key)) return this.get(key)
    const value = callbackFn(key, this)
    this.set(key, value)
    return value
  }
}
