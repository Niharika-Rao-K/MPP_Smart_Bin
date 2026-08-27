export const getStoredUsers = () => JSON.parse(localStorage.getItem('r2e_users')) || [];
export const getActiveWallet = () => localStorage.getItem('r2e_active_wallet') || null;

export const saveDepositToStorage = (depositData) => {
  const existingHistory = JSON.parse(localStorage.getItem('recycle_history') || '[]');
  const updatedHistory = [depositData, ...existingHistory];
  localStorage.setItem('recycle_history', JSON.stringify(updatedHistory));
  return updatedHistory;
};

export const getDepositHistory = () => {
  return JSON.parse(localStorage.getItem('recycle_history') || '[]');
};
