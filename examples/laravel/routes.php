<?php

/**
 * Example Laravel Routes for Mail2printer Integration
 * 
 * Add these routes to your routes/web.php file
 */

use App\Http\Controllers\Mail2PrinterController;

// Mail2printer routes group
Route::prefix('printer')->name('printer.')->middleware(['auth'])->group(function () {
    
    // Dashboard
    Route::get('/', [Mail2PrinterController::class, 'dashboard'])->name('dashboard');
    
    // Jobs
    Route::get('/jobs', [Mail2PrinterController::class, 'jobs'])->name('jobs');
    Route::get('/jobs/{id}', [Mail2PrinterController::class, 'jobStatus'])->name('jobs.status');
    Route::post('/jobs/{id}/cancel', [Mail2PrinterController::class, 'cancelJob'])->name('jobs.cancel');
    
    // Statistics
    Route::get('/statistics', [Mail2PrinterController::class, 'statistics'])->name('statistics');
    
    // Service control
    Route::post('/restart', [Mail2PrinterController::class, 'restart'])->name('restart');
    
    // Health check (no auth required)
    Route::get('/health', [Mail2PrinterController::class, 'health'])->name('health')->withoutMiddleware(['auth']);
});
