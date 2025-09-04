-- Project-specific Neovim configuration for Stellar SDEX
-- This file is automatically sourced when opening the project

-- Set Python path for the project
vim.env.PYTHONPATH = vim.fn.getcwd() .. "/src:" .. (vim.env.PYTHONPATH or "")

-- Activate virtual environment
vim.env.VIRTUAL_ENV = vim.fn.getcwd() .. "/venv"
vim.env.PATH = vim.env.VIRTUAL_ENV .. "/bin:" .. vim.env.PATH

-- Project-specific settings
vim.opt_local.tabstop = 4
vim.opt_local.shiftwidth = 4
vim.opt_local.expandtab = true
vim.opt_local.textwidth = 100

-- Custom commands for this project
vim.api.nvim_create_user_command('StellarTest', function()
    vim.cmd('terminal cd ' .. vim.fn.getcwd() .. ' && python -m pytest test/ -v')
end, {})

vim.api.nvim_create_user_command('StellarLint', function()
    vim.cmd('terminal cd ' .. vim.fn.getcwd() .. ' && python -m flake8 src/ test/')
end, {})

vim.api.nvim_create_user_command('StellarFormat', function()
    vim.cmd('terminal cd ' .. vim.fn.getcwd() .. ' && python -m black src/ test/')
end, {})

vim.api.nvim_create_user_command('StellarType', function()
    vim.cmd('terminal cd ' .. vim.fn.getcwd() .. ' && python -m mypy src/')
end, {})

-- Project-specific keymaps
local opts = { noremap = true, silent = true }
vim.keymap.set("n", "<leader>st", ":StellarTest<CR>", opts)
vim.keymap.set("n", "<leader>sl", ":StellarLint<CR>", opts)
vim.keymap.set("n", "<leader>sf", ":StellarFormat<CR>", opts)
vim.keymap.set("n", "<leader>sy", ":StellarType<CR>", opts)

-- Quick file navigation for project structure
vim.keymap.set("n", "<leader>pci", ":e hummingbot/connector/exchange/stellar/stellar_chain_interface.py<CR>", opts)
vim.keymap.set("n", "<leader>pse", ":e hummingbot/connector/exchange/stellar/stellar_exchange.py<CR>", opts)
vim.keymap.set("n", "<leader>pom", ":e hummingbot/connector/exchange/stellar/stellar_order_manager.py<CR>", opts)
vim.keymap.set("n", "<leader>pam", ":e hummingbot/connector/exchange/stellar/stellar_asset_manager.py<CR>", opts)
vim.keymap.set("n", "<leader>psm", ":e hummingbot/connector/exchange/stellar/stellar_soroban_manager.py<CR>", opts)
vim.keymap.set("n", "<leader>pss", ":e hummingbot/connector/exchange/stellar/stellar_sep_services.py<CR>", opts)

-- Test file navigation
vim.keymap.set("n", "<leader>tci", ":e test/unit/test_stellar_chain.py<CR>", opts)
vim.keymap.set("n", "<leader>tom", ":e test/unit/test_stellar_order_manager.py<CR>", opts)
vim.keymap.set("n", "<leader>tee", ":e test/integration/test_end_to_end_trading.py<CR>", opts)
