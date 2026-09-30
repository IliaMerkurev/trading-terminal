import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
afterEach(cleanup);
globalThis.ResizeObserver=class {observe(){} unobserve(){} disconnect(){}};

// jsdom does not implement the native dialog top layer. Native keyboard behavior requires Windows verification.
if(!HTMLDialogElement.prototype.showModal){
 HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
 HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
}
