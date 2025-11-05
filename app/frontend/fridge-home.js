// ============================== 
// 冷蔵庫ホームページ用スクリプト 
// ============================== 
document.addEventListener("DOMContentLoaded", () => { 
  const backBtn = document.getElementById("backBtn"); 
  const controlBtn = document.getElementById("controlBtn"); 
  const checkBtn = document.getElementById("checkBtn"); 
  
  // ホーム画面に戻る 
  backBtn.addEventListener("click", () => { 
    window.location.href = "home.html";
   }); 
    // 食材の追加・削除ページへ 
    controlBtn.addEventListener("click", () => { 
      window.location.href = "fridge-control.html"; 
    }); 
    // 食材一覧ページへ 
    checkBtn.addEventListener("click", () => { 
      window.location.href = "fridge-check.html"; 
    }); 
  });