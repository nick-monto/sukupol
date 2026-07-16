// Barrel: public surface of the controller package.
export { bindInteractionHandlers, bindNpcSelection } from "./handlers";
export { leaveNpcConversation } from "./dialogue";
export { syncBusyState } from "./state";
export { createPinballRegistry } from "./options";
export type { ControllerOptions, PinballRegistry } from "./options";
