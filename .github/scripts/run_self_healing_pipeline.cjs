// Compatibility entry point: structural repairs never certify financial facts.
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
if (require.main === module) {
  execFileSync(process.env.KANU_PYTHON || 'python', [path.join(__dirname,'repair_accuracy.py')], {cwd:root,stdio:'inherit'});
  execFileSync(process.execPath, [path.join(__dirname,'quality_queue.cjs')], {cwd:root,stdio:'inherit'});
}
