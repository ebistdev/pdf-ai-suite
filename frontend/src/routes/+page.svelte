<script lang="ts">
  interface Table {
    index: number;
    page: number;
    markdown: string;
    csv?: string;
  }
  
  interface ExtractionResult {
    filename: string;
    num_pages: number;
    markdown: string;
    text: string;
    tables: Table[];
    images_extracted: number;
    title?: string;
    headings: { level: number; text: string; page: number }[];
  }
  
  let file: File | null = null;
  let files: FileList | null = null;  // For batch
  let url = '';
  let isLoading = false;
  let error = '';
  let result: ExtractionResult | null = null;
  let summaryResult: SummaryResult | null = null;
  let activeTab = 'markdown';
  let extractImages = true;
  let enableSummary = false;
  let selectedLanguage = 'en';
  let isBatchMode = false;
  let batchResults: BatchResult[] = [];
  
  interface SummaryResult {
    summary: string;
    key_points: string[];
    important_numbers: { value: string; context: string }[];
    tables_summary: { title: string; key_data: string[] }[];
  }
  
  interface BatchResult {
    filename: string;
    success: boolean;
    num_pages?: number;
    tables_count?: number;
    error?: string;
  }
  
  let languages = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'de', name: 'German' },
    { code: 'zh', name: 'Chinese' },
    { code: 'ja', name: 'Japanese' },
    { code: 'ko', name: 'Korean' },
    { code: 'ar', name: 'Arabic' },
    { code: 'ru', name: 'Russian' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'hi', name: 'Hindi' },
    { code: 'it', name: 'Italian' },
  ];
  
  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      file = input.files[0];
      url = '';
    }
  }
  
  function handleDrop(event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
      file = event.dataTransfer.files[0];
      url = '';
    }
  }
  
  function handleDragOver(event: DragEvent) {
    event.preventDefault();
  }
  
  async function extract() {
    if (!file && !url) return;
    
    isLoading = true;
    error = '';
    result = null;
    summaryResult = null;
    
    try {
      let response: Response;
      const endpoint = enableSummary ? '/api/extract/summarize' : '/api/extract';
      
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const params = new URLSearchParams();
        params.append('extract_images', extractImages.toString());
        if (enableSummary) {
          params.append('language', selectedLanguage);
        }
        
        response = await fetch(`${endpoint}?${params}`, {
          method: 'POST',
          body: formData
        });
      } else {
        response = await fetch(`/api/extract/url?url=${encodeURIComponent(url)}&extract_images=${extractImages}`, {
          method: 'POST'
        });
      }
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Extraction failed');
      }
      
      const data = await response.json();
      
      if (enableSummary) {
        summaryResult = {
          summary: data.summary,
          key_points: data.key_points || [],
          important_numbers: data.important_numbers || [],
          tables_summary: data.tables_summary || []
        };
        result = {
          filename: data.filename,
          num_pages: data.num_pages,
          markdown: data.markdown,
          text: data.text,
          tables: [],
          images_extracted: 0,
          title: null,
          headings: []
        };
      } else {
        result = data;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Unknown error';
    } finally {
      isLoading = false;
    }
  }
  
  async function extractBatch() {
    if (!files || files.length === 0) return;
    
    isLoading = true;
    error = '';
    batchResults = [];
    
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }
      
      const response = await fetch('/api/extract/batch?output_format=markdown', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Batch extraction failed');
      }
      
      const data = await response.json();
      batchResults = data.results;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Batch failed';
    } finally {
      isLoading = false;
    }
  }
  
  async function downloadBatchZip() {
    if (!files || files.length === 0) return;
    
    isLoading = true;
    
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }
      
      const response = await fetch('/api/extract/batch/zip?output_format=markdown', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error('Failed to create ZIP');
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'extracted_documents.zip';
      a.click();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Download failed';
    } finally {
      isLoading = false;
    }
  }
  
  function reset() {
    file = null;
    url = '';
    result = null;
    error = '';
  }
  
  function downloadMarkdown() {
    if (!result) return;
    const blob = new Blob([result.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = result.filename.replace(/\.[^.]+$/, '.md');
    a.click();
  }
  
  function downloadText() {
    if (!result) return;
    const blob = new Blob([result.text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = result.filename.replace(/\.[^.]+$/, '.txt');
    a.click();
  }
  
  function downloadTableCSV(table: Table) {
    if (!table.csv) return;
    const blob = new Blob([table.csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `table_${table.index + 1}.csv`;
    a.click();
  }
</script>

<svelte:head>
  <title>PDF AI Suite - Extract Content from Documents</title>
</svelte:head>

<div class="max-w-5xl mx-auto py-8 px-4">
  {#if !result}
    <!-- Upload Section -->
    <div class="text-center mb-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">Extract Content from Any Document</h1>
      <p class="text-xl text-gray-600">Tables, text, images, structure — powered by AI</p>
    </div>
    
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
      <!-- Drop Zone -->
      <div 
        ondrop={handleDrop}
        ondragover={handleDragOver}
        class="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-indigo-400 transition cursor-pointer"
      >
        <input 
          type="file" 
          id="file-input"
          accept=".pdf,.docx,.pptx,.html,.htm,.png,.jpg,.jpeg,.tiff"
          onchange={handleFileSelect}
          class="hidden"
        />
        <label for="file-input" class="cursor-pointer">
          <span class="text-5xl mb-4 block">📁</span>
          {#if file}
            <p class="text-lg font-medium text-gray-900">{file.name}</p>
            <p class="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
          {:else}
            <p class="text-lg font-medium text-gray-900">Drop your document here</p>
            <p class="text-sm text-gray-500">or click to browse</p>
          {/if}
        </label>
      </div>
      
      <div class="my-6 flex items-center">
        <div class="flex-1 border-t border-gray-200"></div>
        <span class="px-4 text-sm text-gray-500">or</span>
        <div class="flex-1 border-t border-gray-200"></div>
      </div>
      
      <!-- URL Input -->
      <div>
        <label for="url" class="block text-sm font-medium text-gray-700 mb-2">
          Extract from URL
        </label>
        <input 
          type="url"
          id="url"
          bind:value={url}
          placeholder="https://example.com/document.pdf"
          class="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-indigo-500"
          oninput={() => file = null}
        />
      </div>
      
      <!-- Options -->
      <div class="mt-6 space-y-4">
        <!-- Mode Toggle -->
        <div class="flex gap-4">
          <button
            onclick={() => isBatchMode = false}
            class="px-4 py-2 rounded-lg text-sm {!isBatchMode ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}"
          >
            Single File
          </button>
          <button
            onclick={() => isBatchMode = true}
            class="px-4 py-2 rounded-lg text-sm {isBatchMode ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}"
          >
            📦 Batch (up to 20)
          </button>
        </div>
        
        {#if isBatchMode}
          <div class="bg-indigo-50 rounded-lg p-4">
            <input 
              type="file" 
              multiple
              accept=".pdf,.docx,.pptx,.html,.htm,.png,.jpg,.jpeg"
              onchange={(e) => files = e.target.files}
              class="w-full"
            />
            <p class="text-sm text-indigo-600 mt-2">
              {files ? `${files.length} files selected` : 'Select multiple files'}
            </p>
          </div>
        {:else}
          <div class="flex flex-wrap gap-4">
            <label class="flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                bind:checked={extractImages}
                class="rounded border-gray-300 text-indigo-600 mr-2"
              />
              <span class="text-sm text-gray-700">Extract images</span>
            </label>
            
            <label class="flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                bind:checked={enableSummary}
                class="rounded border-gray-300 text-indigo-600 mr-2"
              />
              <span class="text-sm text-gray-700">🤖 AI Summary</span>
            </label>
            
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-700">Language:</span>
              <select bind:value={selectedLanguage} class="text-sm border border-gray-300 rounded px-2 py-1">
                {#each languages as lang}
                  <option value={lang.code}>{lang.name}</option>
                {/each}
              </select>
            </div>
          </div>
        {/if}
      </div>
      
      {#if error}
        <div class="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <p class="text-red-700">❌ {error}</p>
        </div>
      {/if}
      
      {#if isBatchMode}
        <div class="mt-6 flex gap-3">
          <button
            onclick={extractBatch}
            disabled={isLoading || !files || files.length === 0}
            class="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isLoading ? 'Processing...' : '📊 Extract All'}
          </button>
          <button
            onclick={downloadBatchZip}
            disabled={isLoading || !files || files.length === 0}
            class="bg-green-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            ⬇️ Download ZIP
          </button>
        </div>
      {:else}
        <button
          onclick={extract}
          disabled={isLoading || (!file && !url)}
          class="mt-6 w-full bg-indigo-600 text-white py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {#if isLoading}
            <span class="inline-flex items-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Extracting...
            </span>
          {:else}
            🚀 Extract Content
          {/if}
        </button>
      {/if}
    </div>
    
    <!-- Supported Formats -->
    <div class="text-center text-sm text-gray-500">
      <p class="mb-2 font-medium">Supported Formats</p>
      <p>PDF • DOCX • PPTX • HTML • PNG • JPG • TIFF</p>
    </div>
    
  {:else if batchResults.length > 0}
    <!-- Batch Results -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Batch Results</h2>
        <p class="text-gray-600">
          {batchResults.filter(r => r.success).length} of {batchResults.length} files processed successfully
        </p>
      </div>
      <button
        onclick={() => { batchResults = []; files = null; }}
        class="text-gray-600 hover:text-gray-900 flex items-center"
      >
        ← Process More
      </button>
    </div>
    
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <table class="w-full">
        <thead class="bg-gray-50">
          <tr>
            <th class="text-left px-4 py-3 text-sm font-medium text-gray-600">File</th>
            <th class="text-center px-4 py-3 text-sm font-medium text-gray-600">Status</th>
            <th class="text-right px-4 py-3 text-sm font-medium text-gray-600">Pages</th>
            <th class="text-right px-4 py-3 text-sm font-medium text-gray-600">Tables</th>
          </tr>
        </thead>
        <tbody>
          {#each batchResults as result}
            <tr class="border-t border-gray-100">
              <td class="px-4 py-3 font-medium">{result.filename}</td>
              <td class="px-4 py-3 text-center">
                {#if result.success}
                  <span class="text-green-600">✓</span>
                {:else}
                  <span class="text-red-600" title={result.error}>✗</span>
                {/if}
              </td>
              <td class="px-4 py-3 text-right text-gray-600">{result.num_pages || '-'}</td>
              <td class="px-4 py-3 text-right text-gray-600">{result.tables_count || '-'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <!-- Results Section -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">{result.filename}</h2>
        <p class="text-gray-600">
          {result.num_pages} pages • {result.tables.length} tables • {result.images_extracted} images
        </p>
      </div>
      <button
        onclick={reset}
        class="text-gray-600 hover:text-gray-900 flex items-center"
      >
        ← New Document
      </button>
    </div>
    
    <!-- Summary Card (if enabled) -->
    {#if summaryResult}
      <div class="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200 p-6 mb-6">
        <h3 class="text-lg font-semibold text-indigo-900 mb-3">🤖 AI Summary</h3>
        <p class="text-gray-700 mb-4">{summaryResult.summary}</p>
        
        {#if summaryResult.key_points.length > 0}
          <div class="mb-4">
            <h4 class="text-sm font-medium text-indigo-800 mb-2">Key Points:</h4>
            <ul class="list-disc list-inside space-y-1">
              {#each summaryResult.key_points as point}
                <li class="text-gray-700 text-sm">{point}</li>
              {/each}
            </ul>
          </div>
        {/if}
        
        {#if summaryResult.important_numbers.length > 0}
          <div>
            <h4 class="text-sm font-medium text-indigo-800 mb-2">Key Numbers:</h4>
            <div class="flex flex-wrap gap-2">
              {#each summaryResult.important_numbers as num}
                <span class="bg-white px-3 py-1 rounded-full text-sm border border-indigo-200">
                  <span class="font-semibold">{num.value}</span>
                  <span class="text-gray-500"> — {num.context}</span>
                </span>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}
    
    <!-- Tabs -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="border-b border-gray-200">
        <nav class="flex -mb-px">
          <button
            onclick={() => activeTab = 'markdown'}
            class="px-6 py-3 text-sm font-medium border-b-2 {activeTab === 'markdown' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}"
          >
            📝 Markdown
          </button>
          <button
            onclick={() => activeTab = 'text'}
            class="px-6 py-3 text-sm font-medium border-b-2 {activeTab === 'text' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}"
          >
            📄 Plain Text
          </button>
          <button
            onclick={() => activeTab = 'tables'}
            class="px-6 py-3 text-sm font-medium border-b-2 {activeTab === 'tables' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}"
          >
            📊 Tables ({result.tables.length})
          </button>
          <button
            onclick={() => activeTab = 'structure'}
            class="px-6 py-3 text-sm font-medium border-b-2 {activeTab === 'structure' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}"
          >
            🏗️ Structure
          </button>
        </nav>
      </div>
      
      <div class="p-6">
        {#if activeTab === 'markdown'}
          <div class="flex justify-end mb-4">
            <button
              onclick={downloadMarkdown}
              class="text-sm text-indigo-600 hover:text-indigo-800"
            >
              ⬇️ Download .md
            </button>
          </div>
          <pre class="bg-gray-50 p-4 rounded-lg overflow-auto max-h-[600px] text-sm whitespace-pre-wrap">{result.markdown}</pre>
        
        {:else if activeTab === 'text'}
          <div class="flex justify-end mb-4">
            <button
              onclick={downloadText}
              class="text-sm text-indigo-600 hover:text-indigo-800"
            >
              ⬇️ Download .txt
            </button>
          </div>
          <pre class="bg-gray-50 p-4 rounded-lg overflow-auto max-h-[600px] text-sm whitespace-pre-wrap">{result.text}</pre>
        
        {:else if activeTab === 'tables'}
          {#if result.tables.length === 0}
            <p class="text-gray-500 text-center py-8">No tables found in this document</p>
          {:else}
            <div class="space-y-6">
              {#each result.tables as table}
                <div class="border border-gray-200 rounded-lg overflow-hidden">
                  <div class="bg-gray-50 px-4 py-2 flex justify-between items-center">
                    <span class="font-medium">Table {table.index + 1} (Page {table.page})</span>
                    {#if table.csv}
                      <button
                        onclick={() => downloadTableCSV(table)}
                        class="text-sm text-indigo-600 hover:text-indigo-800"
                      >
                        ⬇️ CSV
                      </button>
                    {/if}
                  </div>
                  <pre class="p-4 overflow-auto text-sm">{table.markdown}</pre>
                </div>
              {/each}
            </div>
          {/if}
        
        {:else if activeTab === 'structure'}
          <div class="space-y-4">
            {#if result.title}
              <div>
                <span class="font-medium text-gray-700">Title:</span>
                <span class="ml-2">{result.title}</span>
              </div>
            {/if}
            
            <div>
              <span class="font-medium text-gray-700">Headings:</span>
              {#if result.headings.length === 0}
                <p class="text-gray-500 mt-2">No headings detected</p>
              {:else}
                <ul class="mt-2 space-y-1">
                  {#each result.headings as heading}
                    <li class="flex items-center">
                      <span class="text-xs text-gray-400 w-16">Page {heading.page}</span>
                      <span class="ml-{heading.level * 2}">{heading.text}</span>
                    </li>
                  {/each}
                </ul>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
