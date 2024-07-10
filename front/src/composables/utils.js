// useFormatNumber.js
export function useFormatNumber() {
    const formatNumber = (number) => {
      if (number != null) {
        return number.toFixed(2);
      }
      return number;
    };
  
    return { formatNumber };
  }
  