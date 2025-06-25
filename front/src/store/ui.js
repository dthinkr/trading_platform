import { defineStore } from "pinia";

export const useUIStore = defineStore("ui", {
  state: () => ({
    showSnackbar: false,
    snackbarText: "",
    dayOver: false,
    intendedRoute: null,
  }),

  actions: {
    showMessage(text) {
      this.snackbarText = text;
      this.showSnackbar = true;
    },

    hideMessage() {
      this.showSnackbar = false;
      this.snackbarText = "";
    },

    setDayOver(value) {
      this.dayOver = value;
    },

    setIntendedRoute(route) {
      this.intendedRoute = route;
    },

    getIntendedRoute() {
      const route = this.intendedRoute;
      this.intendedRoute = null;
      return route;
    },

    showLimitMessage(gameParams, hasReachedMaxActiveOrders, hasExceededMaxShortCash, hasExceededMaxShortShares) {
      if (hasReachedMaxActiveOrders) {
        this.showMessage(`You are allowed to have a maximum of ${gameParams.max_active_orders} active orders`);
      } else if (hasExceededMaxShortCash) {
        this.showMessage(`You are not allowed to short more than ${gameParams.max_short_cash} cash`);
      } else if (hasExceededMaxShortShares) {
        this.showMessage(`You are not allowed to short more than ${gameParams.max_short_shares} shares`);
      }
    },
  },
}); 