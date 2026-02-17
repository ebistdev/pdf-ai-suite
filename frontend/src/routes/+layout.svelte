<script>
  import '../app.css';
</script>

<div class="min-h-screen flex flex-col">
  <nav class="bg-white border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <div class="flex items-center">
          <a href="/" class="flex items-center">
            <span class="text-2xl mr-2">📄</span>
            <span class="font-bold text-xl text-indigo-600">PDF AI Suite</span>
          </a>
        </div>
        <div class="flex items-center text-sm text-gray-500">
          Extract tables, text, images & more
        </div>
      </div>
    </div>
  </nav>
  
  <main class="flex-1">
    <slot />
  </main>
  
  <footer class="bg-white border-t border-gray-200 py-4">
    <div class="max-w-7xl mx-auto px-4 text-center text-sm text-gray-500">
      PDF AI Suite &copy; 2026 - Powered by Docling
    </div>
  </footer>
</div>
