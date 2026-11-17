<template>
  <div class="notfound">
    <div class="notfound__mark serif">404</div>
    <h1 class="serif">这张牌桌不存在</h1>
    <p>也许它已经散场，或者链接写错了。</p>
    <el-button class="btn-gold" @click="$router.push('/')">回到大厅</el-button>
  </div>
</template>

<style scoped>
.notfound {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
  padding: 20px;
}
.notfound__mark {
  font-size: 72px;
  color: rgba(216, 178, 106, 0.25);
  line-height: 1;
}
.notfound h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 500;
}
.notfound p {
  margin: 0 0 10px;
  font-size: 11px;
  color: var(--muted);
}
</style>
