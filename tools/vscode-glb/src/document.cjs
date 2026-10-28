const fs = require('node:fs/promises');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { readGlb } = require('./assets.cjs');
const { rebaseGlb, editGlb } = require('./glb-edit.cjs');

class GlbDocument {
  constructor(file, bytes, saved = bytes) { readGlb(bytes); this.file = file; this.bytes = bytes; this.saved = saved; }
  get dirty() { return !this.bytes.equals(this.saved); }
  endEdit() { this.liveEdit = undefined; }
  edit(request, { group, shared, managed } = {}) {
    const key = group && JSON.stringify([group, request.kind, request.target, request.scope]);
    const previous = key && this.liveEdit?.key === key && this.liveEdit.after === this.bytes ? this.liveEdit : null;
    const before = previous?.before || this.bytes;
    // Rebuild a gesture from its starting bytes: dragging never stacks UV/paint buffers or material copies.
    const after = editGlb(before, request, this.file, shared, managed);
    if (after.equals(this.bytes)) return null;
    const change = previous || { key, before };
    change.after = this.bytes = after; this.liveEdit = key ? change : undefined;
    return { change, started: !previous };
  }
  async refresh() { if (!this.dirty) { const bytes = await fs.readFile(this.file); readGlb(bytes); this.bytes = this.saved = bytes; } }
  async revert() { this.endEdit(); const bytes = await fs.readFile(this.file); readGlb(bytes); this.bytes = this.saved = bytes; }
  backup() { return Buffer.from(JSON.stringify({ bytes: this.bytes.toString('base64'), saved: this.saved.toString('base64') })); }
  static restore(file, backup) { const data = JSON.parse(backup); return new GlbDocument(file, Buffer.from(data.bytes, 'base64'), Buffer.from(data.saved, 'base64')); }
  async save(target = this.file, token) {
    this.endEdit();
    if (this.saving) throw Error('A GLB save is already running');
    this.saving = true;
    const bytes = this.bytes, saved = this.saved, same = path.relative(this.file, target) === '';
    const temp = path.join(path.dirname(target), `.${path.basename(target)}.${randomUUID()}.tmp`);
    const check = async () => {
      if (token?.isCancellationRequested) throw Error('Save cancelled');
      if (same && !(await fs.readFile(this.file)).equals(saved)) throw Error('GLB changed on disk. Your edits are still open. Use Save As to keep them, or File: Revert File to load the disk version.');
    };
    try {
      await check();
      await fs.writeFile(temp, rebaseGlb(bytes, this.file, target), { flag: 'wx' });
      await check(); await fs.rename(temp, target);
      if (same) this.saved = bytes;
    } finally { this.saving = false; await fs.rm(temp, { force: true }); }
  }
}
module.exports = { GlbDocument };
